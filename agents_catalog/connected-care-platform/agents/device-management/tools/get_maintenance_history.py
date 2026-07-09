"""Tool: Get maintenance history for a device."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
work_orders_table = dynamodb.Table(os.environ.get("DYNAMODB_WORK_ORDERS_TABLE", "connected-care-work-orders"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def get_maintenance_history(device_id: str) -> dict:
    """Retrieve past maintenance records and work orders for a device.

    Args:
        device_id: The device identifier (e.g., D-2001)

    Returns:
        Device maintenance summary including last maintenance date and work order history.
    """
    # Get device profile for last_maintenance_date
    device_resp = devices_table.get_item(Key={"device_id": device_id})
    device = device_resp.get("Item")
    if not device:
        return {"error": f"Device {device_id} not found"}

    # Get work orders for this device
    wo_resp = work_orders_table.query(
        KeyConditionExpression=Key("device_id").eq(device_id),
        ScanIndexForward=False,
    )

    work_orders = []
    for item in wo_resp.get("Items", []):
        work_orders.append({
            "work_order_id": item.get("work_order_id"),
            "created_date": item.get("created_date"),
            "priority": item.get("priority"),
            "description": item.get("description"),
            "status": item.get("status", "open"),
        })

    return {
        "device_id": device_id,
        "device_type": device.get("device_type"),
        "model": device.get("model"),
        "installation_date": device.get("installation_date"),
        "last_maintenance_date": device.get("last_maintenance_date"),
        "work_order_count": len(work_orders),
        "work_orders": work_orders,
    }
