"""Tool: Get alert thresholds for a patient."""

import os
import boto3
from strands import tool
from .phi_access import check_phi_access, phi_access_denied_response

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))


@tool
def get_alert_thresholds(patient_id: str) -> dict:
    """Retrieve the current alert thresholds for a specific patient.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        The patient's personalized alert thresholds for each vital sign type,
        showing the low and high boundaries that trigger alerts.
    """
    if not check_phi_access(patient_id):
        return phi_access_denied_response(patient_id)

    response = patients_table.get_item(Key={"patient_id": patient_id})
    item = response.get("Item")

    if not item:
        return {"error": f"Patient {patient_id} not found"}

    thresholds = item.get("alert_thresholds", {})
    clean = {}
    for vital, bounds in thresholds.items():
        clean[vital] = {
            "low": float(bounds.get("low", 0)),
            "high": float(bounds.get("high", 0)),
        }

    return {
        "patient_id": patient_id,
        "patient_name": item.get("name", "Unknown"),
        "alert_thresholds": clean,
    }
