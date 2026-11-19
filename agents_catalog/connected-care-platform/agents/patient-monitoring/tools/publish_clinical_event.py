"""Tool: Publish clinical events to EventBridge."""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool

eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))
EVENT_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")


@tool
def publish_clinical_event(
    patient_id: str,
    event_type: str,
    severity: str,
    summary: str,
) -> dict:
    """Publish a clinical event to EventBridge for downstream workflow processing.

    Use this tool when you detect a patient is deteriorating (vital_sign.early_warning)
    or when a vital sign is at a critical level (vital_sign.critical).

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        event_type: Either 'vital_sign.early_warning' or 'vital_sign.critical'
        severity: One of 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        summary: Brief clinical summary of why this event is being published

    Returns:
        Confirmation that the event was published with the event ID.
    """
    valid_types = ["vital_sign.early_warning", "vital_sign.critical"]
    if event_type not in valid_types:
        return {"error": f"Invalid event_type '{event_type}'. Must be one of: {valid_types}"}

    valid_severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if severity not in valid_severities:
        return {"error": f"Invalid severity '{severity}'. Must be one of: {valid_severities}"}

    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    event_detail = {
        "eventId": event_id,
        "timestamp": timestamp,
        "patientId": patient_id,
        "severity": severity,
        "triggerSource": "AGENT",
        "payload": {
            "summary": summary,
            "agentName": "Patient Monitoring Agent",
        },
    }

    response = eventbridge.put_events(
        Entries=[
            {
                "Source": "patient-monitoring",
                "DetailType": event_type,
                "Detail": json.dumps(event_detail),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    failed = response.get("FailedEntryCount", 0)
    if failed > 0:
        return {"error": "Failed to publish event to EventBridge", "details": response}

    return {
        "event_id": event_id,
        "event_type": event_type,
        "patient_id": patient_id,
        "severity": severity,
        "timestamp": timestamp,
        "message": f"Clinical event '{event_type}' published successfully for patient {patient_id}",
    }
