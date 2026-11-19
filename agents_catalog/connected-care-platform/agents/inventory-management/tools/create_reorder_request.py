"""Tool: Create a reorder request for a supply item."""

import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
inventory_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory"))
transactions_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TRANSACTIONS_TABLE", "connected-care-inventory-transactions"))


@tool
def create_reorder_request(item_id: str, quantity: int, priority: str, reason: str) -> dict:
    """Create a reorder request for a supply item.

    Args:
        item_id: The inventory item identifier (e.g., INV-001)
        quantity: Number of units to reorder
        priority: One of: routine, urgent, emergency, stat
        reason: Brief explanation for the reorder request

    Returns:
        Confirmation of the reorder request with estimated delivery time.
    """
    valid_priorities = ["routine", "urgent", "emergency", "stat"]
    if priority not in valid_priorities:
        return {"error": f"Invalid priority '{priority}'. Must be one of: {valid_priorities}"}

    inv_resp = inventory_table.get_item(Key={"item_id": item_id})
    item = inv_resp.get("Item")
    if not item:
        return {"error": f"Item {item_id} not found"}

    request_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    lead_time = int(float(item.get("lead_time_hours", 4)))

    # Log the reorder as a transaction
    transactions_table.put_item(Item={
        "item_id": item_id,
        "timestamp": timestamp,
        "transaction_type": "reorder_requested",
        "quantity": quantity,
        "floor": item.get("floor"),
        "patient_id": None,
        "dispensed_by": f"Agent-{request_id[:8]}",
    })

    return {
        "request_id": request_id,
        "item_id": item_id,
        "item_name": item.get("item_name"),
        "floor": item.get("floor"),
        "quantity_requested": quantity,
        "unit": item.get("unit"),
        "priority": priority,
        "reason": reason,
        "supplier": item.get("supplier"),
        "estimated_delivery_hours": lead_time,
        "timestamp": timestamp,
        "message": f"Reorder request created for {quantity} {item.get('unit')} of {item.get('item_name')} ({priority} priority)",
    }
