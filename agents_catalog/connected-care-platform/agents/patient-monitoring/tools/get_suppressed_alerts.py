"""Tool: Retrieve alerts that were suppressed (for audit and review)."""

import os
import boto3
from strands import tool
from datetime import datetime, timedelta, timezone

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
alert_history_table = dynamodb.Table(os.environ.get("ALERT_HISTORY_TABLE", "connected-care-alert-history"))


@tool
def get_suppressed_alerts(nurse_id: str = "", patient_id: str = "", hours: int = 1) -> dict:
    """Retrieve alerts that were suppressed by the alert triage system.

    Useful for audit, review, and understanding what the system filtered out.
    Can filter by nurse or patient.

    Args:
        nurse_id: Filter by nurse (e.g., NRS-001). Optional.
        patient_id: Filter by patient (e.g., P-10001). Optional.
        hours: How many hours of history to retrieve (default: 1)

    Returns:
        List of suppressed alerts with reasons, grouped by suppression type.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # Build filter expression
    filter_parts = ["triage_result = :suppressed", "#ts >= :cutoff"]
    attr_values = {":suppressed": "SUPPRESSED", ":cutoff": cutoff}
    attr_names = {"#ts": "timestamp"}

    if nurse_id:
        filter_parts.append("assigned_nurse_id = :nid")
        attr_values[":nid"] = nurse_id
    if patient_id:
        filter_parts.append("patient_id = :pid")
        attr_values[":pid"] = patient_id

    response = alert_history_table.scan(
        FilterExpression=" AND ".join(filter_parts),
        ExpressionAttributeNames=attr_names,
        ExpressionAttributeValues=attr_values,
        Limit=50,
    )

    items = response.get("Items", [])

    # Group by reason
    by_reason = {}
    for item in items:
        reason = item.get("suppression_reason", "Unknown")
        if reason not in by_reason:
            by_reason[reason] = []
        by_reason[reason].append({
            "alert_id": item.get("alert_id"),
            "patient_id": item.get("patient_id"),
            "alert_type": item.get("alert_type"),
            "severity": item.get("severity"),
            "detail": item.get("detail", ""),
            "timestamp": item.get("timestamp"),
        })

    return {
        "total_suppressed": len(items),
        "period_hours": hours,
        "filter_nurse": nurse_id or "all",
        "filter_patient": patient_id or "all",
        "by_reason": {reason: {"count": len(alerts), "alerts": alerts[:5]} for reason, alerts in by_reason.items()},
        "message": f"{len(items)} alerts were suppressed in the last {hours} hour(s). These were filtered to reduce alert fatigue. All are logged for audit.",
    }
