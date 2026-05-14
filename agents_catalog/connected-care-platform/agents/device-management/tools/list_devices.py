"""Tool: List all devices in the fleet with current status summary."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def list_devices() -> dict:
    """List all devices in the fleet with their current status summary.

    Returns:
        List of all devices with ID, type, model, location, status, and risk profile.
    """
    response = devices_table.scan()
    items = response.get("Items", [])

    devices = []
    for item in items:
        devices.append({
            "device_id": item["device_id"],
            "device_type": item.get("device_type"),
            "model": item.get("model"),
            "location": item.get("location"),
            "status": item.get("status"),
            "risk_profile": item.get("risk_profile"),
            "firmware_version": item.get("firmware_version"),
        })

    devices.sort(key=lambda d: d["device_id"])

    return {
        "total_devices": len(devices),
        "devices": devices,
    }
