"""Tool: Reschedule an existing appointment."""

import os
from datetime import datetime, timezone

import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
appointments_table = dynamodb.Table(os.environ.get("DYNAMODB_APPOINTMENTS_TABLE", "connected-care-appointments"))


@tool
def reschedule_appointment(
    appointment_id: str,
    patient_id: str,
    new_date: str,
    new_time: str,
) -> dict:
    """Reschedule an existing appointment to a new date and time.

    Args:
        appointment_id: The appointment identifier (e.g., APT-001)
        patient_id: The patient identifier (e.g., P-10001)
        new_date: New appointment date in YYYY-MM-DD format
        new_time: New appointment time in HH:MM format

    Returns:
        Confirmation of the rescheduled appointment with old and new details.
    """
    # Verify appointment exists
    apt_resp = appointments_table.get_item(
        Key={"patient_id": patient_id, "appointment_id": appointment_id}
    )
    appointment = apt_resp.get("Item")
    if not appointment:
        return {"error": f"Appointment {appointment_id} not found for patient {patient_id}"}

    old_date = appointment.get("date")
    old_time = appointment.get("time")
    now = datetime.now(timezone.utc).isoformat()

    appointments_table.update_item(
        Key={"patient_id": patient_id, "appointment_id": appointment_id},
        UpdateExpression="SET #d = :new_date, #t = :new_time, updated_at = :now",
        ExpressionAttributeNames={"#d": "date", "#t": "time"},
        ExpressionAttributeValues={
            ":new_date": new_date,
            ":new_time": new_time,
            ":now": now,
        },
    )

    return sanitize({
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "old_date": old_date,
        "old_time": old_time,
        "new_date": new_date,
        "new_time": new_time,
        "message": f"Appointment {appointment_id} rescheduled from {old_date} {old_time} to {new_date} {new_time}",
    })
