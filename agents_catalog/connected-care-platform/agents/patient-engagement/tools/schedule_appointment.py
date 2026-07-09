"""Tool: Schedule a new appointment for a patient."""

import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
appointments_table = dynamodb.Table(os.environ.get("DYNAMODB_APPOINTMENTS_TABLE", "connected-care-appointments"))


@tool
def schedule_appointment(
    patient_id: str,
    appointment_type: str,
    provider: str,
    date: str,
    time: str,
    location: str,
) -> dict:
    """Schedule a new appointment for a patient.

    Creates a new appointment record in DynamoDB with status "scheduled".

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        appointment_type: Type of appointment (e.g., "Cardiology follow-up")
        provider: Provider name (e.g., "Dr. James Park")
        date: Appointment date in YYYY-MM-DD format
        time: Appointment time in HH:MM format
        location: Appointment location (e.g., "Cardiology Clinic B")

    Returns:
        Confirmation of the scheduled appointment with generated appointment ID.
    """
    appointment_id = f"APT-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    appointments_table.put_item(Item={
        "patient_id": patient_id,
        "appointment_id": appointment_id,
        "type": appointment_type,
        "provider": provider,
        "date": date,
        "time": time,
        "location": location,
        "status": "scheduled",
        "created_at": now,
    })

    return sanitize({
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "type": appointment_type,
        "provider": provider,
        "date": date,
        "time": time,
        "location": location,
        "status": "scheduled",
        "message": f"Appointment {appointment_id} scheduled for patient {patient_id} on {date} at {time}",
    })
