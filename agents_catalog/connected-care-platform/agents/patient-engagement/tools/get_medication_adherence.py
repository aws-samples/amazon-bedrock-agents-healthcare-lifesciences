"""Tool: Get per-dose medication adherence records for a patient."""

import os
from datetime import datetime, timedelta, timezone

import boto3
from strands import tool
from boto3.dynamodb.conditions import Key, Attr
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
adherence_table = dynamodb.Table(os.environ.get("DYNAMODB_ADHERENCE_TABLE", "connected-care-medication-adherence"))


@tool
def get_medication_adherence(patient_id: str, days: int = 7) -> dict:
    """Retrieve per-dose adherence records (taken/missed/late) over a time window.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        days: Number of days of history to retrieve (default: 7)

    Returns:
        Adherence records with per-dose status and summary statistics.
    """
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    response = adherence_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
        FilterExpression=Attr("date").gte(cutoff_date),
    )

    items = response.get("Items", [])
    if not items:
        return {"error": f"No adherence records found for patient {patient_id} in the last {days} days"}

    taken = sum(1 for r in items if r.get("status") == "taken")
    missed = sum(1 for r in items if r.get("status") == "missed")
    late = sum(1 for r in items if r.get("status") == "late")
    total = len(items)

    records = []
    for r in items[:50]:  # Limit to 50 most recent records to avoid context window overflow
        records.append({
            "record_id": r.get("record_id"),
            "medication_id": r.get("medication_id"),
            "date": r.get("date"),
            "time": r.get("time"),
            "status": r.get("status"),
        })

    return sanitize({
        "patient_id": patient_id,
        "window_days": days,
        "total_doses": total,
        "taken": taken,
        "missed": missed,
        "late": late,
        "adherence_rate": round((taken / total) * 100, 1) if total > 0 else 0,
        "records_sample": records,
        "records_note": f"Showing 50 of {total} records" if total > 50 else f"Showing all {total} records",
    })
