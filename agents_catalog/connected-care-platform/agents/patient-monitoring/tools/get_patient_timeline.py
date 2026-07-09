"""Tool: Get the full memory timeline for a patient."""

import os
import json
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .phi_access import check_phi_access, phi_access_denied_response

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
memory_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENT_MEMORY_TABLE", "connected-care-patient-memory"))


@tool
def get_patient_timeline(patient_id: str) -> dict:
    """Retrieve the full memory timeline for a patient — all observations, medication changes,
    clinical notes, and events recorded since admission.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Chronological list of all memory entries for the patient.
    """
    if not check_phi_access(patient_id):
        return phi_access_denied_response(patient_id)

    response = memory_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
        ScanIndexForward=True,
    )
    items = response.get("Items", [])

    if not items:
        return {"patient_id": patient_id, "entries": [], "message": "No memory entries found. Patient may not be admitted or memory not initialized."}

    entries = []
    for item in items:
        entry = {
            "timestamp": item.get("timestamp"),
            "entry_type": item.get("entry_type"),
            "category": item.get("category"),
            "summary": item.get("summary"),
            "recorded_by": item.get("recorded_by"),
        }
        if item.get("details"):
            try:
                entry["details"] = json.loads(item["details"])
            except (json.JSONDecodeError, TypeError):
                entry["details"] = item["details"]
        entries.append(entry)

    # Summarize by category
    categories = {}
    for e in entries:
        cat = e.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "patient_id": patient_id,
        "total_entries": len(entries),
        "categories": categories,
        "entries": entries,
    }
