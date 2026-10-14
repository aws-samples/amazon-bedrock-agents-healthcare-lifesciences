"""
Inventory Management Agent — WebSocket Lambda Handler

Handles $connect, $disconnect, and $default (chat messages) routes.
Sends agent responses back to the client via API Gateway callback URL.
"""

import json
import os
import boto3
from strands import Agent
from system_prompt import SYSTEM_PROMPT
from tools import ALL_TOOLS
from config import AGENT_MODEL

agent = Agent(
    model=AGENT_MODEL,
    system_prompt=SYSTEM_PROMPT,
    tools=ALL_TOOLS,
)

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
connections_table = dynamodb.Table(os.environ.get("CONNECTIONS_TABLE", "connected-care-im-connections"))


def get_apigw_client(event):
    """Create API Gateway Management API client from the event context."""
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    endpoint = f"https://{domain}/{stage}"
    return boto3.client("apigatewaymanagementapi", endpoint_url=endpoint)


def send_to_client(event, connection_id, data):
    """Send a message back to the WebSocket client."""
    client = get_apigw_client(event)
    client.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps(data).encode("utf-8"),
    )


def handler(event, context):
    """Lambda handler for WebSocket API Gateway."""

    # Handle orchestrator-internal invocations (direct Lambda invoke)
    if event.get("isOrchestrator"):
        body = json.loads(event.get("body", "{}"))
        prompt = body.get("prompt", "")
        if not prompt:
            return {"statusCode": 200, "body": json.dumps({"response": "Inventory Management Agent ready."})}
        result = agent(prompt)
        response_text = str(result)
        if hasattr(result, "message"):
            msg = result.message
            if isinstance(msg, str): response_text = msg
            elif isinstance(msg, dict):
                content = msg.get("content", [])
                if content and isinstance(content, list): response_text = content[0].get("text", str(msg))
        return {"statusCode": 200, "body": json.dumps({"response": response_text})}

    route_key = event["requestContext"].get("routeKey")
    connection_id = event["requestContext"].get("connectionId")

    if route_key == "$connect":
        connections_table.put_item(Item={"connection_id": connection_id})
        return {"statusCode": 200}

    if route_key == "$disconnect":
        connections_table.delete_item(Key={"connection_id": connection_id})
        return {"statusCode": 200}

    try:
        body = json.loads(event.get("body", "{}"))
        prompt = body.get("prompt", "")

        if not prompt:
            send_to_client(event, connection_id, {
                "type": "response",
                "response": "Hello! I'm the Inventory Management Agent. I can help you track floor inventory, assess stockout risks, and identify how supply shortages affect patient care. What would you like to know?",
            })
            return {"statusCode": 200}

        send_to_client(event, connection_id, {"type": "thinking"})

        result = agent(prompt)

        response_text = str(result)
        if hasattr(result, "message"):
            msg = result.message
            if isinstance(msg, str):
                response_text = msg
            elif isinstance(msg, dict):
                content = msg.get("content", [])
                if content and isinstance(content, list):
                    response_text = content[0].get("text", str(msg))
                else:
                    response_text = str(msg)

        send_to_client(event, connection_id, {
            "type": "response",
            "response": response_text,
        })

        return {"statusCode": 200}

    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}"
        try:
            send_to_client(event, connection_id, {
                "type": "error",
                "response": error_msg,
            })
        except Exception:
            pass
        return {"statusCode": 200}
