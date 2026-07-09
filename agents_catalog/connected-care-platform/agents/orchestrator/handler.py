"""
Orchestrator Agent — WebSocket Lambda Handler

Uses async Lambda invocation pattern to avoid the 29-second WebSocket
integration timeout. The $default route returns immediately, then
invokes itself asynchronously to do the actual work.
"""

import json
import os
import time
import re
import boto3
from config import AGENT_MODEL

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
connections_table = dynamodb.Table(os.environ.get("CONNECTIONS_TABLE", "connected-care-orch-connections"))
lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "us-east-1"))

AGENT_FUNCTIONS = {
    "patient-monitoring": os.environ.get("PM_FUNCTION_NAME", "connected-care-agent-api"),
    "device-management": os.environ.get("DM_FUNCTION_NAME", "connected-care-device-agent-api"),
    "patient-engagement": os.environ.get("PE_FUNCTION_NAME", "connected-care-engagement-agent-api"),
}

AGENT_LABELS = {
    "patient-monitoring": "Patient Monitoring",
    "device-management": "Device Management",
    "patient-engagement": "Patient Engagement",
}

WORKFLOW_KEYWORDS = {
    "WF-01": ["fall", "fell", "fall detection", "fall investigation"],
    "WF-02": ["medication correlation", "anomaly", "anomalous", "medication side effect"],
    "WF-03": ["deteriorat", "cascade", "early warning", "rapid response", "declining"],
    "WF-04": ["device fail", "device offline", "device down", "device impact", "device broke"],
    "WF-05": ["discharge", "post-discharge", "remote monitoring", "going home"],
}


def send_to_client(domain, stage, connection_id, data):
    """Send a message to a WebSocket client."""
    if not domain or not stage:
        return
    client = boto3.client("apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}")
    try:
        client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(data).encode("utf-8"))
    except Exception as e:
        print(f"Failed to send to {connection_id}: {e}")


def detect_workflow(prompt: str):
    lower = prompt.lower()
    for wf_id, keywords in WORKFLOW_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return wf_id
    return None


def invoke_agent(function_name, agent_label, prompt):
    """Invoke a domain agent Lambda directly."""
    from tools.invoke_agent import invoke_agent_lambda
    return invoke_agent_lambda(function_name, agent_label, prompt)


def process_workflow(domain, stage, connection_id, workflow_id, user_prompt):
    """Execute a workflow step-by-step, streaming traces to the client."""
    from workflows import ALL_WORKFLOWS

    workflow = ALL_WORKFLOWS[workflow_id]
    steps = workflow["steps"]
    workflow_name = workflow["name"]

    # Extract parameters
    params = {}
    patient_match = re.search(r'P-\d{5}', user_prompt)
    if patient_match: params["patient_id"] = patient_match.group()
    device_match = re.search(r'D-\d{4}', user_prompt)
    if device_match: params["device_id"] = device_match.group()
    location_match = re.search(r'(ICU-\d+|Floor\d+-\d+)', user_prompt)
    if location_match: params["location"] = location_match.group()

    # Send workflow started
    send_to_client(domain, stage, connection_id, {
        "type": "trace", "workflow": workflow_id, "workflow_name": workflow_name,
        "total_steps": len(steps), "status": "started",
    })

    results = []
    step_responses = {}
    total_start = time.time()

    for step_def in steps:
        step_num = step_def["step"]
        agent_key = step_def["agent"]
        agent_label = AGENT_LABELS.get(agent_key, agent_key)
        description = step_def["description"]
        function_name = AGENT_FUNCTIONS.get(agent_key)

        # Build prompt
        prompt = step_def["prompt_template"]
        for key, value in params.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        for prev in range(1, step_num):
            prompt = prompt.replace(f"{{step_{prev}_response}}", str(step_responses.get(prev, "Not available"))[:500])
        prompt = prompt.replace("{previous_findings}", str(step_responses.get(step_num - 1, "")))

        # Send IN PROGRESS
        send_to_client(domain, stage, connection_id, {
            "type": "trace", "workflow": workflow_id, "step": step_num,
            "total_steps": len(steps), "status": "in_progress",
            "agent": agent_label, "description": description,
        })

        # Invoke agent
        if function_name:
            result = invoke_agent(function_name, agent_label, prompt)
        else:
            result = {"agent": agent_label, "response": "Agent not configured", "duration_ms": 0, "status": "failed"}

        step_responses[step_num] = result.get("response", "")

        # Send COMPLETED + partial response
        send_to_client(domain, stage, connection_id, {
            "type": "trace", "workflow": workflow_id, "step": step_num,
            "total_steps": len(steps), "status": result.get("status", "completed"),
            "agent": agent_label, "description": description,
            "response": result.get("response", "")[:300],
            "duration_ms": result.get("duration_ms", 0),
        })

        # Send step result as a visible message
        send_to_client(domain, stage, connection_id, {
            "type": "partial", "step": step_num, "agent": agent_label,
            "response": f"**Step {step_num}/{len(steps)} — {agent_label}** ({result.get('duration_ms', 0)}ms)\n\n{result.get('response', '')}",
            "duration_ms": result.get("duration_ms", 0),
        })

        results.append(result)

    total_duration = int((time.time() - total_start) * 1000)

    # Send workflow completed
    send_to_client(domain, stage, connection_id, {
        "type": "trace", "workflow": workflow_id, "status": "completed",
        "total_duration_ms": total_duration,
        "steps_completed": len([r for r in results if r.get("status") == "completed"]),
        "steps_failed": len([r for r in results if r.get("status") == "failed"]),
    })

    # Synthesize final summary using the agent
    from strands import Agent
    from system_prompt import SYSTEM_PROMPT
    from tools import ALL_TOOLS

    synth_agent = Agent(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)
    summary_parts = [f"Workflow {workflow_id} ({workflow_name}) completed in {total_duration}ms.\n"]
    for i, step_def in enumerate(steps):
        r = results[i]
        summary_parts.append(f"Step {step_def['step']} ({AGENT_LABELS.get(step_def['agent'])} — {step_def['description']}): {r.get('response', '')[:400]}")

    synth_prompt = f"The user asked: {user_prompt}\n\nWorkflow results:\n\n{'\\n\\n'.join(summary_parts)}\n\nProvide a concise synthesized clinical summary. Do NOT repeat each step."
    synth_result = synth_agent(synth_prompt)

    response_text = str(synth_result)
    if hasattr(synth_result, "message"):
        msg = synth_result.message
        if isinstance(msg, str): response_text = msg
        elif isinstance(msg, dict):
            content = msg.get("content", [])
            if content and isinstance(content, list): response_text = content[0].get("text", str(msg))

    send_to_client(domain, stage, connection_id, {"type": "response", "response": response_text})


def process_adhoc(domain, stage, connection_id, prompt):
    """Handle ad-hoc queries using the agent directly."""
    from strands import Agent
    from system_prompt import SYSTEM_PROMPT
    from tools import ALL_TOOLS

    ag = Agent(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)
    result = ag(prompt)
    response_text = str(result)
    if hasattr(result, "message"):
        msg = result.message
        if isinstance(msg, str): response_text = msg
        elif isinstance(msg, dict):
            content = msg.get("content", [])
            if content and isinstance(content, list): response_text = content[0].get("text", str(msg))

    send_to_client(domain, stage, connection_id, {"type": "response", "response": response_text})


def handler(event, context):
    # --- EventBridge ---
    if "requestContext" not in event and ("source" in event or "detail-type" in event):
        print(f"EventBridge: {event.get('detail-type', 'unknown')}")
        return {"statusCode": 200}

    # --- Async worker invocation (from ourselves) ---
    if event.get("_async_work"):
        work = event["_async_work"]
        domain = work["domain"]
        stage = work["stage"]
        connection_id = work["connection_id"]
        prompt = work["prompt"]

        try:
            workflow_id = detect_workflow(prompt)
            if workflow_id:
                process_workflow(domain, stage, connection_id, workflow_id, prompt)
            else:
                process_adhoc(domain, stage, connection_id, prompt)
        except Exception as e:
            import traceback
            print(f"Async error: {traceback.format_exc()}")
            send_to_client(domain, stage, connection_id, {"type": "error", "response": f"Error: {str(e)}"})

        return {"statusCode": 200}

    # --- WebSocket routes ---
    route_key = event.get("requestContext", {}).get("routeKey")
    connection_id = event.get("requestContext", {}).get("connectionId")

    if route_key == "$connect":
        connections_table.put_item(Item={"connection_id": connection_id})
        return {"statusCode": 200}

    if route_key == "$disconnect":
        connections_table.delete_item(Key={"connection_id": connection_id})
        return {"statusCode": 200}

    # --- $default: return immediately, invoke async worker ---
    body = json.loads(event.get("body", "{}"))
    prompt = body.get("prompt", "")
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]

    if not prompt:
        send_to_client(domain, stage, connection_id, {
            "type": "response",
            "response": "I'm the Orchestrator Agent. Try: \"Device D-4001 has failed. What's the patient impact?\"",
        })
        return {"statusCode": 200}

    # Send thinking immediately
    send_to_client(domain, stage, connection_id, {"type": "thinking"})

    # Invoke ourselves asynchronously — this returns immediately
    lambda_client.invoke(
        FunctionName=context.function_name,
        InvocationType="Event",  # Async — returns immediately
        Payload=json.dumps({
            "_async_work": {
                "domain": domain,
                "stage": stage,
                "connection_id": connection_id,
                "prompt": prompt,
            }
        }),
    )

    # Return 200 immediately — the async invocation handles the rest
    return {"statusCode": 200}
