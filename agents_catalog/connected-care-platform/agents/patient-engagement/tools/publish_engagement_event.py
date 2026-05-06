"""Tool: Publish patient engagement events to EventBridge."""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool
from .sanitize import sanitize

eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))
EVENT_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")


@tool
def publish_engagement_event(
    patient_id: str,
    event_type: str,
    severity: str,
    summary: str,
) -> dict:
    """Publish a patient engagement event to EventBridge for downstream workflow processing.

    Use this tool when you detect engagement issues, schedule changes,
    or need to notify other systems about patient engagement activities.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        event_type: One of: patient.notification_sent, appointment.noshow_predicted,
                    patient.discharged, medication.adherence_alert, appointment.scheduled,
                    appointment.cancelled, patient.onboarded, caregiver.notified,
                    care_plan.created, telehealth.requested, communication.preference_updated
        severity: One of: LOW, MEDIUM, HIGH, CRITICAL
        summary: Brief summary of why this event is being published

    Returns:
        Confirmation that the event was published with the event ID.
    """
    valid_types = [
        "patient.notification_sent",
        "appointment.noshow_predicted",
        "patient.discharged",
        "medication.adherence_alert",
        "appointment.scheduled",
        "appointment.cancelled",
        "patient.onboarded",
        "caregiver.notified",
        "care_plan.created",
        "telehealth.requested",
        "communication.preference_updated",
    ]
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
            "agentName": "Patient Engagement Agent",
        },
    }

    response = eventbridge.put_events(
        Entries=[
            {
                "Source": "patient-engagement",
                "DetailType": event_type,
                "Detail": json.dumps(event_detail),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    failed = response.get("FailedEntryCount", 0)
    if failed > 0:
        return {"error": "Failed to publish event to EventBridge", "details": response}

    return sanitize({
        "event_id": event_id,
        "event_type": event_type,
        "patient_id": patient_id,
        "severity": severity,
        "timestamp": timestamp,
        "message": f"Engagement event '{event_type}' published successfully for patient {patient_id}",
    })
