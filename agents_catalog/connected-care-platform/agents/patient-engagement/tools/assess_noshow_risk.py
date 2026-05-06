"""Tool: Assess no-show risk for a patient's upcoming appointment."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key, Attr
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
appointments_table = dynamodb.Table(os.environ.get("DYNAMODB_APPOINTMENTS_TABLE", "connected-care-appointments"))


@tool
def assess_noshow_risk(patient_id: str, appointment_id: str) -> dict:
    """Assess the no-show risk for a specific upcoming appointment.

    Retrieves appointment history, calculates attendance rate, and returns
    risk factors and risk level for the agent to reason about.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        appointment_id: The appointment identifier (e.g., APT-001)

    Returns:
        Risk assessment with attendance rate, risk factors, and risk level (LOW/MODERATE/HIGH).
    """
    # Get the target appointment
    apt_resp = appointments_table.get_item(
        Key={"patient_id": patient_id, "appointment_id": appointment_id}
    )
    appointment = apt_resp.get("Item")
    if not appointment:
        return {"error": f"Appointment {appointment_id} not found for patient {patient_id}"}

    # Get all past appointments (not scheduled)
    history_resp = appointments_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
        FilterExpression=Attr("status").ne("scheduled"),
    )
    past_appointments = history_resp.get("Items", [])

    risk_factors = []
    total_past = len(past_appointments)

    if total_past == 0:
        return sanitize({
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "appointment_type": appointment.get("type"),
            "appointment_date": appointment.get("date"),
            "risk_level": "MODERATE",
            "risk_factors": ["No appointment history available — cannot assess pattern"],
            "attendance_rate": None,
            "past_appointments_count": 0,
        })

    attended = sum(1 for a in past_appointments if a.get("status") == "attended")
    missed = sum(1 for a in past_appointments if a.get("status") == "missed")
    cancelled = sum(1 for a in past_appointments if a.get("status") == "cancelled")
    attendance_rate = round((attended / total_past) * 100, 1)

    # Assess risk factors
    if missed > 0:
        risk_factors.append(f"Patient has {missed} missed appointment(s) in history")
    if cancelled > 0:
        risk_factors.append(f"Patient has {cancelled} cancelled appointment(s) in history")
    if attendance_rate < 70:
        risk_factors.append(f"Low attendance rate: {attendance_rate}%")
    if total_past < 3:
        risk_factors.append("Limited appointment history for reliable prediction")

    # Determine risk level
    if attendance_rate >= 90 and missed == 0:
        risk_level = "LOW"
    elif attendance_rate >= 70:
        risk_level = "MODERATE"
    else:
        risk_level = "HIGH"

    return sanitize({
        "patient_id": patient_id,
        "appointment_id": appointment_id,
        "appointment_type": appointment.get("type"),
        "appointment_date": appointment.get("date"),
        "appointment_provider": appointment.get("provider"),
        "risk_level": risk_level,
        "risk_factors": risk_factors if risk_factors else ["No significant risk factors identified"],
        "attendance_rate": attendance_rate,
        "past_appointments_count": total_past,
        "attended": attended,
        "missed": missed,
        "cancelled": cancelled,
    })
