"""Tool: Get current medications for a patient."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
medications_table = dynamodb.Table(os.environ.get("DYNAMODB_MEDICATIONS_TABLE", "connected-care-medications"))


@tool
def get_medication_list(patient_id: str) -> dict:
    """Retrieve the current medication list for a patient.

    Includes dose, frequency, prescriber, side effects, refill info, and change history.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        List of current medications with full details.
    """
    response = medications_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
    )

    items = response.get("Items", [])
    if not items:
        return {"error": f"No medications found for patient {patient_id}"}

    medications = []
    for med in items:
        medications.append({
            "medication_id": med.get("medication_id"),
            "name": med.get("name"),
            "dose": med.get("dose"),
            "frequency": med.get("frequency"),
            "prescriber": med.get("prescriber"),
            "start_date": med.get("start_date"),
            "side_effects": med.get("side_effects", []),
            "refill_due": med.get("refill_due"),
            "refills_remaining": int(med.get("refills_remaining", 0)),
            "change_history": med.get("change_history", []),
        })

    return sanitize({
        "patient_id": patient_id,
        "medication_count": len(medications),
        "medications": medications,
    })
