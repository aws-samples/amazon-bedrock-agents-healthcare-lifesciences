"""Tool: Get telemetry history for a device over a time window."""

import os
from datetime import datetime, timedelta, timezone

import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))


@tool
def get_device_history(device_id: str, hours: int = 4) -> dict:
    """Retrieve telemetry history for a device over a configurable time window.

    Args:
        device_id: The device identifier (e.g., D-2001)
        hours: Number of hours of history to retrieve (default: 4)

    Returns:
        List of telemetry readings with timestamps for trend analysis.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    response = telemetry_table.query(
        KeyConditionExpression=Key("device_id").eq(device_id) & Key("timestamp").gte(cutoff),
        ScanIndexForward=True,
    )

    items = response.get("Items", [])
    if not items:
        return {"error": f"No telemetry found for device {device_id} in the last {hours} hours"}

    readings = []
    for item in items:
        t = item.get("telemetry", {})
        readings.append({
            "timestamp": item["timestamp"],
            "battery_level": float(t.get("battery_level", 0)),
            "connectivity_status": t.get("connectivity_status", "unknown"),
            "sensor_accuracy": float(t.get("sensor_accuracy", 0)),
            "error_count": int(t.get("error_count", 0)),
            "calibration_drift": float(t.get("calibration_drift", 0)),
            "device_temperature": float(t.get("device_temperature", 0)),
            "memory_usage": float(t.get("memory_usage", 0)),
            "signal_strength": float(t.get("signal_strength", 0)),
        })

    return {
        "device_id": device_id,
        "hours": hours,
        "reading_count": len(readings),
        "readings": readings,
    }
