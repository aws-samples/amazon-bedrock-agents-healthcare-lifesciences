"""Tool: Get chronological medication change history for a patient."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
medications_table = dynamodb.Table(os.environ.get("DYNAMODB_MEDICATIONS_TABLE", "connected-care-medications"))


@tool
def get_medication_change_history(patient_id: str) -> dict:
    """Retrieve a chronological list of all medication changes for a patient.

    Extracts change_history from each medication and returns a unified,
    chronologically sorted list of all changes.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Chronological list of medication changes across all medications.
    """
    response = medications_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
    )
    items = response.get("Items", [])
    if not items:
        return {"error": f"No medications found for patient {patient_id}"}

    all_changes = []
    for med in items:
        med_name = med.get("name", "Unknown")
        med_id = med.get("medication_id")
        change_history = med.get("change_history", [])
        for change in change_history:
            all_changes.append({
                "medication_id": med_id,
                "medication_name": med_name,
                "date": change.get("date"),
                "change": change.get("change"),
                "reason": change.get("reason"),
            })

    # Sort chronologically
    all_changes.sort(key=lambda c: c.get("date", ""))

    return sanitize({
        "patient_id": patient_id,
        "total_changes": len(all_changes),
        "changes": all_changes,
    })
