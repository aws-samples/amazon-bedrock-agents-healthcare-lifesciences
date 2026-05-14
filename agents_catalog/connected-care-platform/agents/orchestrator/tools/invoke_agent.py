"""Shared utility: Invoke a domain agent — supports both Lambda and AgentCore modes.

When running on AgentCore with a request_id, writes trace events to DynamoDB
so the frontend can poll for step-by-step progress.

Tool call tracking: Each invoke_* tool writes its prompt to the trace as a tool_call.
This is deterministic — we know exactly what the orchestrator asked each agent.
"""

import json
import os
import time
import boto3

lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "us-east-1"))

AGENTCORE_MODE = bool(os.environ.get("PM_RUNTIME_ARN"))

if AGENTCORE_MODE:
    agentcore_client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))

TRACES_TABLE = os.environ.get("TRACES_TABLE", "connected-care-agent-traces")
_current_request_id = ""

AGENT_KEYS = {
    "Patient Monitoring": "patient-monitoring",
    "Device Management": "device-management",
    "Patient Engagement": "patient-engagement",
    "Inventory Management": "inventory-management",
    "Field Service": "field-service",
    "Account Intelligence": "account-intelligence",
}

try:
    dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    traces_table = dynamodb.Table(TRACES_TABLE)
except Exception:
    traces_table = None


def set_request_id(request_id: str):
    global _current_request_id
    _current_request_id = request_id


def _write_trace(agent_label: str, status: str, duration_ms: int = 0,
                 response_preview: str = "", error: str = "",
                 prompt: str = ""):
    """Write a trace event to DynamoDB."""
    if not _current_request_id or not traces_table:
        return
    agent_key = AGENT_KEYS.get(agent_label, agent_label.lower().replace(" ", "-"))
    try:
        item = {
            "request_id": _current_request_id,
            "sort_key": f"trace#{int(time.time() * 1000)}#{agent_key}",
            "type": "trace",
            "agent": agent_key,
            "status": status,
            "timestamp": int(time.time() * 1000),
        }
        if duration_ms:
            item["duration_ms"] = duration_ms
        if response_preview:
            item["response_preview"] = response_preview[:300]
        if error:
            item["error"] = error[:500]
        if prompt:
            # Store the prompt the orchestrator sent — this IS the tool call
            item["tool_calls"] = json.dumps([{
                "tool": f"invoke_{agent_key.replace('-', '_')}",
                "input": prompt[:200],
            }])
        traces_table.put_item(Item=item)
    except Exception as e:
        print(f"Trace write failed: {e}")


def invoke_agent_lambda(function_name: str, agent_label: str, prompt: str) -> dict:
    _write_trace(agent_label, "in_progress", prompt=prompt)
    start = time.time()
    try:
        event = {
            "requestContext": {"routeKey": "$default", "connectionId": "orchestrator-internal",
                               "domainName": "orchestrator", "stage": "internal"},
            "body": json.dumps({"prompt": prompt}),
            "isOrchestrator": True,
        }
        response = lambda_client.invoke(FunctionName=function_name,
                                        InvocationType="RequestResponse",
                                        Payload=json.dumps(event))
        duration_ms = int((time.time() - start) * 1000)
        result = json.loads(response["Payload"].read())
        body = result.get("body", "")
        if isinstance(body, str):
            try: body = json.loads(body)
            except: pass
        response_text = body.get("response", str(body)) if isinstance(body, dict) else str(body)
        _write_trace(agent_label, "completed", duration_ms, response_text)
        return {"agent": agent_label, "response": response_text,
                "duration_ms": duration_ms, "status": "completed"}
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        _write_trace(agent_label, "failed", duration_ms, error=str(e))
        return {"agent": agent_label, "response": f"Agent unavailable: {str(e)}",
                "duration_ms": duration_ms, "status": "failed"}


def invoke_agent_agentcore(runtime_arn: str, agent_label: str, prompt: str) -> dict:
    _write_trace(agent_label, "in_progress", prompt=prompt)
    start = time.time()
    try:
        payload = json.dumps({"prompt": prompt}).encode()
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId="orchestrator-" + str(int(time.time() * 1000)).ljust(33, '0'),
            payload=payload,
            qualifier="DEFAULT",
        )
        duration_ms = int((time.time() - start) * 1000)
        response_body = response["response"].read()
        response_data = json.loads(response_body)

        response_text = ""
        if isinstance(response_data, dict):
            inner = response_data.get("result", response_data)
            if isinstance(inner, dict):
                response_text = inner.get("response", str(inner))
            elif isinstance(inner, str):
                response_text = inner
            else:
                response_text = str(inner)
        else:
            response_text = str(response_data)

        _write_trace(agent_label, "completed", duration_ms, response_text)
        return {"agent": agent_label, "response": response_text,
                "duration_ms": duration_ms, "status": "completed"}
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        _write_trace(agent_label, "failed", duration_ms, error=str(e))
        return {"agent": agent_label, "response": f"Agent unavailable: {str(e)}",
                "duration_ms": duration_ms, "status": "failed"}


def invoke_agent(function_name_or_arn: str, agent_label: str, prompt: str) -> dict:
    if AGENTCORE_MODE and function_name_or_arn.startswith("arn:"):
        return invoke_agent_agentcore(function_name_or_arn, agent_label, prompt)
    return invoke_agent_lambda(function_name_or_arn, agent_label, prompt)
