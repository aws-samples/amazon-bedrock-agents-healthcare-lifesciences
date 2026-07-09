"""Tool: Create a maintenance work order for a device."""

import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
work_orders_table = dynamodb.Table(os.environ.get("DYNAMODB_WORK_ORDERS_TABLE", "connected-care-work-orders"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def create_maintenance_work_order(device_id: str, priority: str, description: str) -> dict:
    """Create a maintenance work order for a device.

    Args:
        device_id: The device identifier (e.g., D-2001)
        priority: Work order priority — one of: low, medium, high, critical
        description: Description of the maintenance needed

    Returns:
        Confirmation with work order ID and details.
    """
    valid_priorities = ["low", "medium", "high", "critical"]
    if priority not in valid_priorities:
        return {"error": f"Invalid priority '{priority}'. Must be one of: {valid_priorities}"}

    # Verify device exists
    device_resp = devices_table.get_item(Key={"device_id": device_id})
    if not device_resp.get("Item"):
        return {"error": f"Device {device_id} not found"}

    work_order_id = f"WO-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    work_orders_table.put_item(Item={
        "device_id": device_id,
        "work_order_id": work_order_id,
        "created_date": now,
        "priority": priority,
        "description": description,
        "status": "open",
        "device_type": device_resp["Item"].get("device_type"),
        "device_model": device_resp["Item"].get("model"),
        "location": device_resp["Item"].get("location"),
    })

    return {
        "work_order_id": work_order_id,
        "device_id": device_id,
        "priority": priority,
        "description": description,
        "created_date": now,
        "status": "open",
        "message": f"Work order {work_order_id} created for device {device_id} with {priority} priority",
    }
