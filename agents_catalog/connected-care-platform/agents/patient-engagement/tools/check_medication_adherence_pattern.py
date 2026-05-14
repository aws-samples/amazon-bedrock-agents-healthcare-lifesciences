"""Tool: Check medication adherence patterns and flag low-adherence medications."""

import os
from collections import defaultdict

import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
adherence_table = dynamodb.Table(os.environ.get("DYNAMODB_ADHERENCE_TABLE", "connected-care-medication-adherence"))
medications_table = dynamodb.Table(os.environ.get("DYNAMODB_MEDICATIONS_TABLE", "connected-care-medications"))


@tool
def check_medication_adherence_pattern(patient_id: str) -> dict:
    """Analyze medication adherence patterns for a patient.

    Queries all adherence records, calculates per-medication adherence rates,
    and flags medications below the 80% adherence threshold.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Per-medication adherence rates with flagged low-adherence medications.
    """
    # Get adherence records
    adherence_resp = adherence_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
    )
    records = adherence_resp.get("Items", [])
    if not records:
        return {"error": f"No adherence records found for patient {patient_id}"}

    # Get medication names for context
    med_resp = medications_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
    )
    med_lookup = {m["medication_id"]: m.get("name", "Unknown") for m in med_resp.get("Items", [])}

    # Calculate per-medication stats
    med_stats = defaultdict(lambda: {"taken": 0, "missed": 0, "late": 0, "total": 0})
    for r in records:
        med_id = r.get("medication_id")
        status = r.get("status")
        med_stats[med_id]["total"] += 1
        if status in ("taken", "missed", "late"):
            med_stats[med_id][status] += 1

    ADHERENCE_THRESHOLD = 80.0
    medications = []
    flagged = []

    for med_id, stats in med_stats.items():
        total = stats["total"]
        taken = stats["taken"]
        rate = round((taken / total) * 100, 1) if total > 0 else 0
        med_name = med_lookup.get(med_id, "Unknown")

        entry = {
            "medication_id": med_id,
            "medication_name": med_name,
            "total_doses": total,
            "taken": taken,
            "missed": stats["missed"],
            "late": stats["late"],
            "adherence_rate": rate,
            "below_threshold": rate < ADHERENCE_THRESHOLD,
        }
        medications.append(entry)
        if rate < ADHERENCE_THRESHOLD:
            flagged.append({"medication_id": med_id, "medication_name": med_name, "adherence_rate": rate})

    overall_taken = sum(s["taken"] for s in med_stats.values())
    overall_total = sum(s["total"] for s in med_stats.values())
    overall_rate = round((overall_taken / overall_total) * 100, 1) if overall_total > 0 else 0

    return sanitize({
        "patient_id": patient_id,
        "overall_adherence_rate": overall_rate,
        "adherence_threshold": ADHERENCE_THRESHOLD,
        "total_records": overall_total,
        "medications": medications,
        "flagged_medications": flagged,
        "flagged_count": len(flagged),
    })
