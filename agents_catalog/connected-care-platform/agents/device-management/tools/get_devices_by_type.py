"""Tool: List all devices of a specific type."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def get_devices_by_type(device_type: str) -> dict:
    """List all devices of a specific type with their current status.

    Args:
        device_type: The device type (vital_signs_monitor, infusion_pump, ventilator, wearable, smart_home_sensor)

    Returns:
        List of devices matching the specified type.
    """
    valid_types = ["vital_signs_monitor", "infusion_pump", "ventilator", "wearable", "smart_home_sensor"]
    if device_type not in valid_types:
        return {"error": f"Invalid device_type '{device_type}'. Must be one of: {valid_types}"}

    response = devices_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("device_type").eq(device_type),
    )

    items = response.get("Items", [])
    devices = []
    for item in items:
        devices.append({
            "device_id": item["device_id"],
            "model": item.get("model"),
            "location": item.get("location"),
            "status": item.get("status"),
            "risk_profile": item.get("risk_profile"),
            "firmware_version": item.get("firmware_version"),
        })

    devices.sort(key=lambda d: d["device_id"])

    return {
        "device_type": device_type,
        "count": len(devices),
        "devices": devices,
    }
