"""Tool: Get current vital signs for a patient."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .phi_access import check_phi_access, phi_access_denied_response

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
vitals_table = dynamodb.Table(os.environ.get("DYNAMODB_VITALS_TABLE", "connected-care-vitals"))


@tool
def get_patient_vitals(patient_id: str) -> dict:
    """Retrieve the most recent vital signs for a specific patient.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        The most recent vital sign readings including heart rate, blood pressure,
        temperature, SpO2, respiratory rate, and blood glucose.
    """
    if not check_phi_access(patient_id):
        return phi_access_denied_response(patient_id)

    response = vitals_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
        ScanIndexForward=False,
        Limit=1,
    )

    if not response.get("Items"):
        return {"error": f"No vital signs found for patient {patient_id}"}

    item = response["Items"][0]
    vitals = item.get("vitals", {})

    return {
        "patient_id": patient_id,
        "timestamp": item["timestamp"],
        "heart_rate": {"value": float(vitals.get("heart_rate", 0)), "unit": "bpm"},
        "blood_pressure_systolic": {"value": float(vitals.get("blood_pressure_systolic", 0)), "unit": "mmHg"},
        "blood_pressure_diastolic": {"value": float(vitals.get("blood_pressure_diastolic", 0)), "unit": "mmHg"},
        "temperature": {"value": float(vitals.get("temperature", 0)), "unit": "°F"},
        "spo2": {"value": float(vitals.get("spo2", 0)), "unit": "%"},
        "respiratory_rate": {"value": float(vitals.get("respiratory_rate", 0)), "unit": "breaths/min"},
        "blood_glucose": {"value": float(vitals.get("blood_glucose", 0)), "unit": "mg/dL"},
    }
