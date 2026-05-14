"""Tool: Send a notification to a patient via their preferred channel."""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
profiles_table = dynamodb.Table(os.environ.get("DYNAMODB_ENGAGEMENT_PROFILES_TABLE", "connected-care-engagement-profiles"))
communications_table = dynamodb.Table(os.environ.get("DYNAMODB_COMMUNICATIONS_TABLE", "connected-care-communications"))
eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))
EVENT_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")


@tool
def send_notification(
    patient_id: str,
    notification_type: str,
    content: str,
) -> dict:
    """Send a notification to a patient via their preferred communication channel.

    Looks up the patient's preferred channel from their engagement profile,
    logs the communication to the communications table, and publishes a
    patient.notification_sent event to EventBridge.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        notification_type: Type of notification (e.g., "appointment_reminder", "medication_reminder", "adherence_alert")
        content: The notification message content

    Returns:
        Confirmation of the sent notification with channel and log details.
    """
    # Look up patient's preferred channel
    profile_resp = profiles_table.get_item(Key={"patient_id": patient_id})
    profile = profile_resp.get("Item")
    if not profile:
        return {"error": f"No engagement profile found for patient {patient_id}"}

    prefs = profile.get("communication_preferences", {})
    channel = prefs.get("preferred_channel", "sms")

    # Log to communications table
    log_id = f"LOG-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    communications_table.put_item(Item={
        "patient_id": patient_id,
        "log_id": log_id,
        "timestamp": now,
        "channel": channel,
        "type": notification_type,
        "content": content,
        "status": "delivered",
    })

    # Publish event to EventBridge
    event_id = str(uuid.uuid4())
    event_detail = {
        "eventId": event_id,
        "timestamp": now,
        "patientId": patient_id,
        "severity": "LOW",
        "triggerSource": "AGENT",
        "payload": {
            "notificationType": notification_type,
            "channel": channel,
            "logId": log_id,
            "agentName": "Patient Engagement Agent",
        },
    }

    eventbridge.put_events(
        Entries=[
            {
                "Source": "patient-engagement",
                "DetailType": "patient.notification_sent",
                "Detail": json.dumps(event_detail),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    return sanitize({
        "log_id": log_id,
        "patient_id": patient_id,
        "channel": channel,
        "notification_type": notification_type,
        "content": content,
        "status": "delivered",
        "timestamp": now,
        "message": f"Notification sent to patient {patient_id} via {channel}",
    })
