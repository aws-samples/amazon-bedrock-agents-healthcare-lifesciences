"""
Patient Monitoring Agent — WebSocket Lambda Handler

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

# Initialize agent at module level (reused across warm invocations)
agent = Agent(
    model=AGENT_MODEL,
    system_prompt=SYSTEM_PROMPT,
    tools=ALL_TOOLS,
)

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
connections_table = dynamodb.Table(os.environ.get("CONNECTIONS_TABLE", "connected-care-pm-connections"))


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
            return {"statusCode": 200, "body": json.dumps({"response": "Patient Monitoring Agent ready."})}
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

    # ---- $connect ----
    if route_key == "$connect":
        connections_table.put_item(Item={"connection_id": connection_id})
        return {"statusCode": 200}

    # ---- $disconnect ----
    if route_key == "$disconnect":
        connections_table.delete_item(Key={"connection_id": connection_id})
        return {"statusCode": 200}

    # ---- $default (chat message) ----
    try:
        body = json.loads(event.get("body", "{}"))
        prompt = body.get("prompt", "")

        if not prompt:
            send_to_client(event, connection_id, {
                "type": "response",
                "response": "Hello! I'm the Patient Monitoring Agent. I can help you monitor patient vitals, analyze trends, and assess deterioration risk. What would you like to know?",
            })
            return {"statusCode": 200}

        # Send "thinking" indicator
        send_to_client(event, connection_id, {"type": "thinking"})

        # Invoke agent
        result = agent(prompt)

        # Extract text
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

        # Send response back to client
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
            pass  # Connection may already be closed
        return {"statusCode": 200}
