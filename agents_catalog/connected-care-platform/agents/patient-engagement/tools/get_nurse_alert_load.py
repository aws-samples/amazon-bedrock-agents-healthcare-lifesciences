"""Tool: Get current alert workload metrics for a nurse."""

import os
import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
assignments_table = dynamodb.Table(os.environ.get("NURSE_ASSIGNMENTS_TABLE", "connected-care-nurse-assignments"))
workload_table = dynamodb.Table(os.environ.get("NURSE_WORKLOAD_TABLE", "connected-care-nurse-workload"))


@tool
def get_nurse_alert_load(identifier: str) -> dict:
    """Get current alert workload and cognitive load metrics for a nurse.

    Can look up by nurse_id (e.g., NRS-001) or nurse name (e.g., Maria Santos).

    Args:
        identifier: Nurse ID (NRS-xxx) or nurse name

    Returns:
        Alert counts, response times, cognitive load score, and recommendations.
    """
    nurse_id = identifier
    nurse_name = ""

    # If name provided, find the nurse ID
    if not identifier.startswith("NRS-"):
        response = assignments_table.scan(Limit=20)
        for item in response.get("Items", []):
            if identifier.lower() in item.get("name", "").lower():
                nurse_id = item["nurse_id"]
                nurse_name = item.get("name", "")
                break
        if not nurse_name:
            return {"error": f"No nurse found matching '{identifier}'"}

    # Get assignment info
    assign_resp = assignments_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("nurse_id").eq(nurse_id),
        ScanIndexForward=False,
        Limit=1,
    )
    assignment = assign_resp.get("Items", [{}])[0] if assign_resp.get("Items") else {}
    if not nurse_name:
        nurse_name = assignment.get("name", nurse_id)

    # Get workload metrics
    workload_resp = workload_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("nurse_id").eq(nurse_id),
        ScanIndexForward=False,
        Limit=1,
    )
    workload = workload_resp.get("Items", [{}])[0] if workload_resp.get("Items") else {}

    alerts_pending = int(workload.get("alerts_pending", 0))
    alerts_received = int(workload.get("alerts_received", 0))
    cognitive_load = int(workload.get("cognitive_load_score", 0))
    suppressed = int(workload.get("suppressed_count", 0))

    # Determine load level
    if cognitive_load >= 70:
        load_level = "HIGH"
        recommendation = "Consider redistributing low-priority patients to backup nurse."
    elif cognitive_load >= 40:
        load_level = "MODERATE"
        recommendation = "Manageable load. Monitor for escalation."
    else:
        load_level = "LOW"
        recommendation = "Alert load is healthy."

    return sanitize({
        "nurse_id": nurse_id,
        "name": nurse_name,
        "role": assignment.get("role", ""),
        "shift": f"{assignment.get('shift_start', '')[:16]} to {assignment.get('shift_end', '')[:16]}",
        "patients_assigned": len(assignment.get("assigned_patients", [])),
        "assigned_patients": assignment.get("assigned_patients", []),
        "assigned_rooms": assignment.get("assigned_rooms", []),
        "alerts_this_hour": alerts_received,
        "alerts_pending": alerts_pending,
        "alerts_acknowledged": int(workload.get("alerts_acknowledged", 0)),
        "avg_response_time_seconds": int(workload.get("avg_response_time_seconds", 0)),
        "cognitive_load_score": cognitive_load,
        "load_level": load_level,
        "suppressed_this_hour": suppressed,
        "recommendation": recommendation,
    })
