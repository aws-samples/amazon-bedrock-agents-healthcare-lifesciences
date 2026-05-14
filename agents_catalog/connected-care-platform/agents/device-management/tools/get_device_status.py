"""Tool: Get current status and latest telemetry for a device."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))


@tool
def get_device_status(device_id: str) -> dict:
    """Retrieve the current status and latest telemetry for a specific device.

    Args:
        device_id: The device identifier (e.g., D-2001)

    Returns:
        Device profile summary plus the most recent telemetry readings.
    """
    # Get device profile
    device_resp = devices_table.get_item(Key={"device_id": device_id})
    device = device_resp.get("Item")
    if not device:
        return {"error": f"Device {device_id} not found"}

    # Get latest telemetry
    telemetry_resp = telemetry_table.query(
        KeyConditionExpression=Key("device_id").eq(device_id),
        ScanIndexForward=False,
        Limit=1,
    )

    telemetry = {}
    telemetry_timestamp = None
    if telemetry_resp.get("Items"):
        item = telemetry_resp["Items"][0]
        telemetry = item.get("telemetry", {})
        telemetry_timestamp = item.get("timestamp")

    return {
        "device_id": device_id,
        "device_type": device.get("device_type"),
        "model": device.get("model"),
        "location": device.get("location"),
        "status": device.get("status"),
        "risk_profile": device.get("risk_profile"),
        "firmware_version": device.get("firmware_version"),
        "latest_firmware": device.get("latest_firmware"),
        "last_maintenance_date": device.get("last_maintenance_date"),
        "telemetry_timestamp": telemetry_timestamp,
        "battery_level": float(telemetry.get("battery_level", 0)),
        "connectivity_status": telemetry.get("connectivity_status", "unknown"),
        "sensor_accuracy": float(telemetry.get("sensor_accuracy", 0)),
        "error_count": int(telemetry.get("error_count", 0)),
        "calibration_drift": float(telemetry.get("calibration_drift", 0)),
        "device_temperature": float(telemetry.get("device_temperature", 0)),
        "memory_usage": float(telemetry.get("memory_usage", 0)),
        "signal_strength": float(telemetry.get("signal_strength", 0)),
        "uptime_hours": int(telemetry.get("uptime_hours", 0)),
        "usage_cycles": int(telemetry.get("usage_cycles", 0)),
    }
