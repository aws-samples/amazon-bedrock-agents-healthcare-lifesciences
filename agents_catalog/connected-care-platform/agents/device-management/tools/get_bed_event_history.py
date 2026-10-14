"""Tool: Get bed exit and repositioning event history for a smart bed."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))


@tool
def get_bed_event_history(identifier: str, hours: int = 24) -> dict:
    """Retrieve bed exit events and repositioning history for a smart bed.

    Can look up by device_id (e.g., D-7001) or patient_id (e.g., P-10001).

    Args:
        identifier: Either a device ID (D-7xxx) or patient ID (P-1xxxx)
        hours: Number of hours of history to retrieve (default: 24)

    Returns:
        Bed exit events, repositioning log, and summary statistics.
    """
    device_id = identifier

    # If patient ID, find the smart bed
    if identifier.startswith("P-"):
        scan_resp = devices_table.scan(
            FilterExpression="device_type = :dt AND assigned_patient_id = :pid",
            ExpressionAttributeValues={":dt": "smart_bed", ":pid": identifier},
        )
        items = scan_resp.get("Items", [])
        if not items:
            return {"error": f"No smart bed found for patient {identifier}"}
        device_id = items[0]["device_id"]

    # Get latest telemetry for current state
    telemetry_resp = telemetry_table.query(
        KeyConditionExpression=Key("device_id").eq(device_id),
        ScanIndexForward=False,
        Limit=1,
    )

    if not telemetry_resp.get("Items"):
        return {"error": f"No telemetry data for smart bed {device_id}"}

    item = telemetry_resp["Items"][0]
    t = item.get("telemetry", {})

    # Since we have seed data with current state, synthesize a realistic event history
    # In production, this would query a bed_events table
    return {
        "device_id": device_id,
        "patient_id": item.get("patient_id"),
        "period_hours": hours,
        "current_state": {
            "bed_position": t.get("bed_position"),
            "hours_since_reposition": float(t.get("hours_since_reposition", 0)),
            "last_repositioned": t.get("last_repositioned"),
            "last_bed_exit": t.get("last_bed_exit"),
            "restlessness_score": float(t.get("restlessness_score", 0)),
        },
        "summary": {
            "total_bed_exits": 3,
            "nighttime_exits": 1,
            "repositioning_count": 8,
            "avg_time_between_repositions_hours": 2.1,
            "max_time_without_reposition_hours": float(t.get("hours_since_reposition", 0)),
            "avg_restlessness_score": float(t.get("restlessness_score", 0)),
        },
        "repositioning_compliance": {
            "target_interval_hours": 2.0,
            "compliant_intervals": 6,
            "overdue_intervals": 2,
            "compliance_rate": 75.0,
        },
    }
