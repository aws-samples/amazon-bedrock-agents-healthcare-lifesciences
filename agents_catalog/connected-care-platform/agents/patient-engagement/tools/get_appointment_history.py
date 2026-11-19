"""Tool: Get past appointments with attendance status."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key, Attr
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
appointments_table = dynamodb.Table(os.environ.get("DYNAMODB_APPOINTMENTS_TABLE", "connected-care-appointments"))


@tool
def get_appointment_history(patient_id: str) -> dict:
    """Retrieve past appointments for a patient with attendance status.

    Returns appointments that are not currently scheduled (attended, missed, cancelled).

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        List of past appointments with type, provider, date, and attendance status.
    """
    response = appointments_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
        FilterExpression=Attr("status").ne("scheduled"),
    )

    items = response.get("Items", [])
    if not items:
        return {"error": f"No appointment history found for patient {patient_id}"}

    attended = sum(1 for a in items if a.get("status") == "attended")
    missed = sum(1 for a in items if a.get("status") == "missed")
    cancelled = sum(1 for a in items if a.get("status") == "cancelled")

    appointments = []
    for apt in items:
        appointments.append({
            "appointment_id": apt.get("appointment_id"),
            "type": apt.get("type"),
            "provider": apt.get("provider"),
            "date": apt.get("date"),
            "time": apt.get("time"),
            "location": apt.get("location"),
            "status": apt.get("status"),
        })

    return sanitize({
        "patient_id": patient_id,
        "total_past_appointments": len(items),
        "attended": attended,
        "missed": missed,
        "cancelled": cancelled,
        "attendance_rate": round((attended / len(items)) * 100, 1) if items else 0,
        "appointments": appointments,
    })
