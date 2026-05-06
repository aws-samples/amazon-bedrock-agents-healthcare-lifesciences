"""Field Service Intelligence Agent — WebSocket Lambda Handler"""

import json
import os
import boto3
from strands import Agent
from system_prompt import SYSTEM_PROMPT
from tools import ALL_TOOLS
from config import AGENT_MODEL

agent = Agent(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
connections_table = dynamodb.Table(os.environ.get("CONNECTIONS_TABLE", "connected-care-fs-connections"))


def get_apigw_client(event):
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    return boto3.client("apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}")


def send_to_client(event, connection_id, data):
    get_apigw_client(event).post_to_connection(ConnectionId=connection_id, Data=json.dumps(data).encode("utf-8"))


def handler(event, context):
    if event.get("isOrchestrator"):
        body = json.loads(event.get("body", "{}"))
        prompt = body.get("prompt", "")
        if not prompt:
            return {"statusCode": 200, "body": json.dumps({"response": "Field Service Agent ready."})}
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
            send_to_client(event, connection_id, {"type": "response", "response": "Hello! I'm the Field Service Intelligence Agent. I can help you manage your installed base, predict service needs, and plan FSE dispatches across your hospital customers."})
            return {"statusCode": 200}
        send_to_client(event, connection_id, {"type": "thinking"})
        result = agent(prompt)
        response_text = str(result)
        if hasattr(result, "message"):
            msg = result.message
            if isinstance(msg, str): response_text = msg
            elif isinstance(msg, dict):
                content = msg.get("content", [])
                if content and isinstance(content, list): response_text = content[0].get("text", str(msg))
                else: response_text = str(msg)
        send_to_client(event, connection_id, {"type": "response", "response": response_text})
        return {"statusCode": 200}
    except Exception as e:
        try:
            send_to_client(event, connection_id, {"type": "error", "response": f"Error: {str(e)}"})
        except Exception:
            pass
        return {"statusCode": 200}
