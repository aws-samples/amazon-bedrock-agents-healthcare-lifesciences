"""Tool: Get full patient profile."""

import os
import boto3
from strands import tool
from .phi_access import check_phi_access, phi_access_denied_response

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))


@tool
def get_patient_profile(patient_id: str) -> dict:
    """Retrieve the full profile for a specific patient including demographics,
    conditions, medications, and alert thresholds.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Complete patient profile with demographics, active conditions,
        current medications, and personalized alert thresholds.
    """
    if not check_phi_access(patient_id):
        return phi_access_denied_response(patient_id)
    response = patients_table.get_item(Key={"patient_id": patient_id})
    item = response.get("Item")

    if not item:
        return {"error": f"Patient {patient_id} not found"}

    # Convert Decimal types to float for JSON serialization
    thresholds = item.get("alert_thresholds", {})
    clean_thresholds = {}
    for vital, bounds in thresholds.items():
        clean_thresholds[vital] = {
            "low": float(bounds.get("low", 0)),
            "high": float(bounds.get("high", 0)),
        }

    medications = item.get("medications", [])
    clean_meds = []
    for med in medications:
        clean_meds.append({
            "name": med.get("name", ""),
            "dose": med.get("dose", ""),
            "frequency": med.get("frequency", ""),
        })

    return {
        "patient_id": item["patient_id"],
        "name": item.get("name", "Unknown"),
        "age": int(item.get("age", 0)),
        "gender": item.get("gender", "Unknown"),
        "mrn": item.get("mrn", ""),
        "room": item.get("room", "Unknown"),
        "risk_profile": item.get("risk_profile", "unknown"),
        "conditions": item.get("conditions", []),
        "medications": clean_meds,
        "alert_thresholds": clean_thresholds,
    }
