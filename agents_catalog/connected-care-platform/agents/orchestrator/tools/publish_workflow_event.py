"""Tool: Publish workflow lifecycle events to EventBridge."""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool

eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))
EVENT_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")


@tool
def publish_workflow_event(workflow_id: str, event_type: str, summary: str) -> dict:
    """Publish a workflow lifecycle event to EventBridge.

    Args:
        workflow_id: The workflow identifier (e.g., WF-04)
        event_type: One of: workflow.started, workflow.completed, workflow.failed
        summary: Brief summary of the workflow status

    Returns:
        Confirmation with event ID.
    """
    valid_types = ["workflow.started", "workflow.completed", "workflow.failed"]
    if event_type not in valid_types:
        return {"error": f"Invalid event_type. Must be one of: {valid_types}"}

    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    eventbridge.put_events(Entries=[{
        "Source": "orchestrator",
        "DetailType": event_type,
        "Detail": json.dumps({
            "eventId": event_id,
            "timestamp": timestamp,
            "workflowId": workflow_id,
            "severity": "LOW",
            "triggerSource": "AGENT",
            "payload": {"summary": summary, "agentName": "Orchestrator Agent"},
        }),
        "EventBusName": EVENT_BUS_NAME,
    }])

    return {"event_id": event_id, "event_type": event_type, "workflow_id": workflow_id, "message": f"Workflow event '{event_type}' published for {workflow_id}"}
