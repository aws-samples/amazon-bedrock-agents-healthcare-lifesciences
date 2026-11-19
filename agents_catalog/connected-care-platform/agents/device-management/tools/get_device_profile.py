"""Tool: Get full device profile."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def get_device_profile(device_id: str) -> dict:
    """Retrieve the full profile for a specific device including type, model, serial number,
    firmware, location, installation date, and maintenance history.

    Args:
        device_id: The device identifier (e.g., D-2001)

    Returns:
        Complete device profile with all metadata.
    """
    response = devices_table.get_item(Key={"device_id": device_id})
    item = response.get("Item")

    if not item:
        return {"error": f"Device {device_id} not found"}

    return {
        "device_id": item["device_id"],
        "device_type": item.get("device_type"),
        "model": item.get("model"),
        "serial_number": item.get("serial_number"),
        "location": item.get("location"),
        "floor": item.get("floor"),
        "firmware_version": item.get("firmware_version"),
        "latest_firmware": item.get("latest_firmware"),
        "installation_date": item.get("installation_date"),
        "last_maintenance_date": item.get("last_maintenance_date"),
        "status": item.get("status"),
        "risk_profile": item.get("risk_profile"),
        "notes": item.get("notes"),
    }
