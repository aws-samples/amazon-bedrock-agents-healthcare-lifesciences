"""Tool: Update alert thresholds for a patient."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))

VALID_VITALS = [
    "heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic",
    "temperature", "spo2", "respiratory_rate", "blood_glucose",
]


@tool
def update_alert_threshold(patient_id: str, vital_sign: str, low: float, high: float) -> dict:
    """Update the alert threshold for a specific vital sign for a patient.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        vital_sign: The vital sign type (e.g., heart_rate, blood_pressure_systolic, spo2)
        low: The new low threshold value
        high: The new high threshold value

    Returns:
        Confirmation of the updated threshold.
    """
    if vital_sign not in VALID_VITALS:
        return {"error": f"Invalid vital sign '{vital_sign}'. Valid options: {VALID_VITALS}"}

    if low >= high:
        return {"error": f"Low threshold ({low}) must be less than high threshold ({high})"}

    # Verify patient exists
    response = patients_table.get_item(Key={"patient_id": patient_id})
    if not response.get("Item"):
        return {"error": f"Patient {patient_id} not found"}

    from decimal import Decimal

    patients_table.update_item(
        Key={"patient_id": patient_id},
        UpdateExpression="SET alert_thresholds.#vital = :bounds",
        ExpressionAttributeNames={"#vital": vital_sign},
        ExpressionAttributeValues={
            ":bounds": {"low": Decimal(str(low)), "high": Decimal(str(high))}
        },
    )

    return {
        "patient_id": patient_id,
        "vital_sign": vital_sign,
        "updated_threshold": {"low": low, "high": high},
        "message": f"Alert threshold for {vital_sign} updated successfully",
    }
