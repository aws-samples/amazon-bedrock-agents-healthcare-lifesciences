"""Tool: Analyze device telemetry trends for failure pattern detection."""

import os
from datetime import datetime, timedelta, timezone

import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def analyze_device_telemetry(device_id: str, hours: int = 4) -> dict:
    """Retrieve and format telemetry trends for a device so the agent can reason about failure patterns.

    Provides first reading, last reading, and computed deltas for each metric to enable
    trend analysis and failure prediction.

    Args:
        device_id: The device identifier (e.g., D-2001)
        hours: Number of hours of history to analyze (default: 4)

    Returns:
        Trend analysis data including first/last readings and deltas for each metric.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    response = telemetry_table.query(
        KeyConditionExpression=Key("device_id").eq(device_id) & Key("timestamp").gte(cutoff),
        ScanIndexForward=True,
    )

    items = response.get("Items", [])
    if not items:
        return {"error": f"No telemetry found for device {device_id} in the last {hours} hours"}

    # Get device profile for context
    device_resp = devices_table.get_item(Key={"device_id": device_id})
    device = device_resp.get("Item", {})

    first = items[0].get("telemetry", {})
    last = items[-1].get("telemetry", {})

    numeric_metrics = [
        "battery_level", "sensor_accuracy", "error_count",
        "calibration_drift", "device_temperature", "memory_usage", "signal_strength",
    ]

    trends = {}
    for metric in numeric_metrics:
        first_val = float(first.get(metric, 0))
        last_val = float(last.get(metric, 0))
        delta = round(last_val - first_val, 2)
        direction = "rising" if delta > 0 else "falling" if delta < 0 else "stable"
        trends[metric] = {
            "first": first_val,
            "last": last_val,
            "delta": delta,
            "direction": direction,
        }

    return {
        "device_id": device_id,
        "device_type": device.get("device_type"),
        "model": device.get("model"),
        "risk_profile": device.get("risk_profile"),
        "analysis_window_hours": hours,
        "reading_count": len(items),
        "first_timestamp": items[0]["timestamp"],
        "last_timestamp": items[-1]["timestamp"],
        "connectivity_first": first.get("connectivity_status", "unknown"),
        "connectivity_last": last.get("connectivity_status", "unknown"),
        "trends": trends,
    }
