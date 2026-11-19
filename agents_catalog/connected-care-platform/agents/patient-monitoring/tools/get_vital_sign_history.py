"""Tool: Get vital sign history/trends for a patient."""

import os
from datetime import datetime, timedelta, timezone

import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .phi_access import check_phi_access, phi_access_denied_response

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
vitals_table = dynamodb.Table(os.environ.get("DYNAMODB_VITALS_TABLE", "connected-care-vitals"))


@tool
def get_vital_sign_history(patient_id: str, hours: int = 4) -> dict:
    """Retrieve vital sign history for a patient over a time window.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        hours: Number of hours of history to retrieve (default: 4, max: 24)

    Returns:
        A list of vital sign readings over the requested time window,
        ordered from oldest to newest.
    """
    if not check_phi_access(patient_id):
        return phi_access_denied_response(patient_id)
    hours = min(hours, 24)
    start_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    response = vitals_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id) & Key("timestamp").gte(start_time),
        ScanIndexForward=True,
    )

    items = response.get("Items", [])
    if not items:
        return {
            "patient_id": patient_id,
            "hours": hours,
            "readings_count": 0,
            "readings": [],
            "message": f"No readings found for patient {patient_id} in the last {hours} hours",
        }

    readings = []
    for item in items:
        vitals = item.get("vitals", {})
        readings.append({
            "timestamp": item["timestamp"],
            "heart_rate": float(vitals.get("heart_rate", 0)),
            "blood_pressure_systolic": float(vitals.get("blood_pressure_systolic", 0)),
            "blood_pressure_diastolic": float(vitals.get("blood_pressure_diastolic", 0)),
            "temperature": float(vitals.get("temperature", 0)),
            "spo2": float(vitals.get("spo2", 0)),
            "respiratory_rate": float(vitals.get("respiratory_rate", 0)),
            "blood_glucose": float(vitals.get("blood_glucose", 0)),
        })

    return {
        "patient_id": patient_id,
        "hours": hours,
        "readings_count": len(readings),
        "readings": readings,
    }
