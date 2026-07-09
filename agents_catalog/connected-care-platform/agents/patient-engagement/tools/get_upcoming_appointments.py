"""Tool: Get scheduled future appointments for a patient."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key, Attr
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
appointments_table = dynamodb.Table(os.environ.get("DYNAMODB_APPOINTMENTS_TABLE", "connected-care-appointments"))


@tool
def get_upcoming_appointments(patient_id: str) -> dict:
    """Retrieve scheduled future appointments for a patient.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        List of upcoming scheduled appointments with details.
    """
    response = appointments_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
        FilterExpression=Attr("status").eq("scheduled"),
    )

    items = response.get("Items", [])
    if not items:
        return {"error": f"No upcoming appointments found for patient {patient_id}"}

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
        "upcoming_count": len(appointments),
        "appointments": appointments,
    })
