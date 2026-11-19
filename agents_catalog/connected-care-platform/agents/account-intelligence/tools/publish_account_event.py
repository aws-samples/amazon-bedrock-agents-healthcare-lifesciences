"""Tool: Publish account intelligence events to EventBridge."""

import json
import os
import uuid
from datetime import datetime, timezone
import boto3
from strands import tool

eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))
EVENT_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")


@tool
def publish_account_event(event_type: str, severity: str, summary: str, site_id: str = "") -> dict:
    """Publish an account intelligence event to EventBridge.

    Args:
        event_type: One of: account.renewal_risk, account.health_decline, account.churn_signal
        severity: One of: LOW, MEDIUM, HIGH, CRITICAL
        summary: Brief summary of the event
        site_id: Optional site ID

    Returns:
        Confirmation with event ID.
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    eventbridge.put_events(Entries=[{
        "Source": "account-intelligence",
        "DetailType": event_type,
        "Detail": json.dumps({
            "eventId": event_id, "timestamp": timestamp, "siteId": site_id,
            "severity": severity, "triggerSource": "AGENT",
            "payload": {"summary": summary, "agentName": "Account Intelligence Agent"},
        }),
        "EventBusName": EVENT_BUS_NAME,
    }])

    return {"event_id": event_id, "event_type": event_type, "severity": severity, "timestamp": timestamp, "message": f"Event '{event_type}' published"}
