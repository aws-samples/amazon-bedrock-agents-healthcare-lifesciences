"""Tool: Update a device's operational status."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def update_device_status(device_id: str, new_status: str) -> dict:
    """Update the operational status of a device.

    Args:
        device_id: The device identifier (e.g., D-2001)
        new_status: New status — one of: active, maintenance, offline, decommissioned

    Returns:
        Confirmation of the status update.
    """
    valid_statuses = ["active", "maintenance", "offline", "decommissioned"]
    if new_status not in valid_statuses:
        return {"error": f"Invalid status '{new_status}'. Must be one of: {valid_statuses}"}

    # Verify device exists
    device_resp = devices_table.get_item(Key={"device_id": device_id})
    if not device_resp.get("Item"):
        return {"error": f"Device {device_id} not found"}

    old_status = device_resp["Item"].get("status")

    devices_table.update_item(
        Key={"device_id": device_id},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": new_status},
    )

    return {
        "device_id": device_id,
        "previous_status": old_status,
        "new_status": new_status,
        "message": f"Device {device_id} status updated from '{old_status}' to '{new_status}'",
    }
