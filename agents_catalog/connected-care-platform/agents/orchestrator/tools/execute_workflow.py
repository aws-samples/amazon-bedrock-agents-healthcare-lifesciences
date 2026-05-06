"""Tool: Execute a cross-module workflow step by step."""

import json
import os
import time
import boto3
from strands import tool
from .invoke_agent import invoke_agent as invoke_agent_fn

AGENT_FUNCTIONS = {
    "patient-monitoring": os.environ.get("PM_RUNTIME_ARN") or os.environ.get("PM_FUNCTION_NAME", "connected-care-agent-api"),
    "device-management": os.environ.get("DM_RUNTIME_ARN") or os.environ.get("DM_FUNCTION_NAME", "connected-care-device-agent-api"),
    "patient-engagement": os.environ.get("PE_RUNTIME_ARN") or os.environ.get("PE_FUNCTION_NAME", "connected-care-engagement-agent-api"),
    "inventory-management": os.environ.get("IM_RUNTIME_ARN") or os.environ.get("IM_FUNCTION_NAME", "connected-care-inventory-agent-api"),
    "field-service": os.environ.get("FS_RUNTIME_ARN") or os.environ.get("FS_FUNCTION_NAME", "connected-care-field-service-agent-api"),
    "account-intelligence": os.environ.get("AI_RUNTIME_ARN") or os.environ.get("AI_FUNCTION_NAME", "connected-care-account-intelligence-agent-api"),
}

AGENT_LABELS = {
    "patient-monitoring": "Patient Monitoring",
    "device-management": "Device Management",
    "patient-engagement": "Patient Engagement",
    "inventory-management": "Inventory Management",
    "field-service": "Field Service",
    "account-intelligence": "Account Intelligence",
}

# Global callback for sending trace messages to the frontend
_trace_callback = None


def set_trace_callback(callback):
    """Set the callback function for sending trace messages to the frontend."""
    global _trace_callback
    _trace_callback = callback


def _send_trace(data):
    """Send a trace message if a callback is registered."""
    if _trace_callback:
        _trace_callback(data)


@tool
def execute_workflow(workflow_id: str, parameters: str) -> dict:
    """Execute a cross-module workflow step by step, sending real-time trace messages.

    Args:
        workflow_id: The workflow identifier (WF-01 through WF-05)
        parameters: JSON string of workflow parameters (e.g., patient_id, device_id, location)

    Returns:
        Workflow execution results with per-step responses and timing.
    """
    from workflows import ALL_WORKFLOWS

    workflow = ALL_WORKFLOWS.get(workflow_id)
    if not workflow:
        return {"error": f"Unknown workflow: {workflow_id}. Valid: {list(ALL_WORKFLOWS.keys())}"}

    try:
        params = json.loads(parameters) if isinstance(parameters, str) else parameters
    except json.JSONDecodeError:
        params = {"raw_input": parameters}

    workflow_name = workflow["name"]
    steps = workflow["steps"]
    total_steps = len(steps)

    _send_trace({
        "type": "trace",
        "workflow": workflow_id,
        "workflow_name": workflow_name,
        "total_steps": total_steps,
        "status": "started",
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

        # Build prompt from template, substituting parameters and previous step responses
        prompt = step_def["prompt_template"]
        for key, value in params.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        # Substitute previous step responses
        prompt = prompt.replace("{previous_findings}", json.dumps(step_responses.get(step_num - 1, "")))
        for prev_step in range(1, step_num):
            prompt = prompt.replace(f"{{step_{prev_step}_response}}", str(step_responses.get(prev_step, "Not available")))

        # Send IN PROGRESS trace
        _send_trace({
            "type": "trace",
            "workflow": workflow_id,
            "step": step_num,
            "total_steps": total_steps,
            "status": "in_progress",
            "agent": agent_label,
            "description": description,
            "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
        })

        # Invoke the domain agent
        if not function_name:
            result = {"agent": agent_label, "response": "Agent not configured", "duration_ms": 0, "status": "failed"}
        else:
            result = invoke_agent_fn(function_name, agent_label, prompt)

        step_responses[step_num] = str(result.get("response", ""))

        # Send COMPLETED/FAILED trace
        _send_trace({
            "type": "trace",
            "workflow": workflow_id,
            "step": step_num,
            "total_steps": total_steps,
            "status": result.get("status", "completed"),
            "agent": agent_label,
            "description": description,
            "response": str(result.get("response", ""))[:500],
            "duration_ms": result.get("duration_ms", 0),
        })

        results.append({
            "step": step_num,
            "agent": agent_label,
            "description": description,
            "status": result.get("status", "completed"),
            "response": str(result.get("response", "")),
            "duration_ms": result.get("duration_ms", 0),
        })

    total_duration = int((time.time() - total_start) * 1000)

    # Send workflow completed trace
    _send_trace({
        "type": "trace",
        "workflow": workflow_id,
        "status": "completed",
        "total_duration_ms": total_duration,
        "steps_completed": len([r for r in results if r["status"] == "completed"]),
        "steps_failed": len([r for r in results if r["status"] == "failed"]),
    })

    return {
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "status": "completed",
        "total_duration_ms": total_duration,
        "steps": results,
    }
