"""Tool: Cancel an existing appointment."""

import os
from datetime import datetime, timezone

import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
appointments_table = dynamodb.Table(os.environ.get("DYNAMODB_APPOINTMENTS_TABLE", "connected-care-appointments"))


@tool
def cancel_appointment(
    appointment_id: str,
    patient_id: str,
    reason: str,
) -> dict:
    """Cancel an existing appointment.

    Updates the appointment status to "cancelled" and records the reason.

    Args:
        appointment_id: The appointment identifier (e.g., APT-001)
        patient_id: The patient identifier (e.g., P-10001)
        reason: Reason for cancellation

    Returns:
        Confirmation of the cancelled appointment.
    """
    # Verify appointment exists
    apt_resp = appointments_table.get_item(
        Key={"patient_id": patient_id, "appointment_id": appointment_id}
    )
    appointment = apt_resp.get("Item")
    if not appointment:
        return {"error": f"Appointment {appointment_id} not found for patient {patient_id}"}

    now = datetime.now(timezone.utc).isoformat()

    appointments_table.update_item(
        Key={"patient_id": patient_id, "appointment_id": appointment_id},
        UpdateExpression="SET #s = :status, cancellation_reason = :reason, cancelled_at = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": "cancelled",
            ":reason": reason,
            ":now": now,
        },
    )

    return sanitize({
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "status": "cancelled",
        "reason": reason,
        "cancelled_at": now,
        "message": f"Appointment {appointment_id} for patient {patient_id} has been cancelled",
    })
