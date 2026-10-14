"""Tool: Publish field service events to EventBridge."""

import json
import os
import uuid
from datetime import datetime, timezone
import boto3
from strands import tool

eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))
EVENT_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")


@tool
def publish_field_service_event(event_type: str, severity: str, summary: str, site_id: str = "") -> dict:
    """Publish a field service event to EventBridge.

    Args:
        event_type: One of: field_service.dispatch_created, field_service.safety_signal, field_service.firmware_alert
        severity: One of: LOW, MEDIUM, HIGH, CRITICAL
        summary: Brief summary of the event
        site_id: Optional site ID for site-specific events

    Returns:
        Confirmation with event ID.
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    event_detail = {
        "eventId": event_id,
        "timestamp": timestamp,
        "siteId": site_id,
        "severity": severity,
        "triggerSource": "AGENT",
        "payload": {"summary": summary, "agentName": "Field Service Intelligence Agent"},
    }

    eventbridge.put_events(Entries=[{
        "Source": "field-service",
        "DetailType": event_type,
        "Detail": json.dumps(event_detail),
        "EventBusName": EVENT_BUS_NAME,
    }])

    return {"event_id": event_id, "event_type": event_type, "severity": severity, "timestamp": timestamp, "message": f"Event '{event_type}' published"}
