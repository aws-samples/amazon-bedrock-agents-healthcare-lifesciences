"""Tool: Check pending orders and supply chain status for an item."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
transactions_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TRANSACTIONS_TABLE", "connected-care-inventory-transactions"))
inventory_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory"))


@tool
def get_supply_chain_status(item_id: str) -> dict:
    """Check pending reorder requests and supply chain status for an inventory item.

    Args:
        item_id: The inventory item identifier (e.g., INV-001)

    Returns:
        Pending orders, supplier info, and estimated delivery times.
    """
    inv_resp = inventory_table.get_item(Key={"item_id": item_id})
    item = inv_resp.get("Item")
    if not item:
        return {"error": f"Item {item_id} not found"}

    txn_resp = transactions_table.query(
        KeyConditionExpression=Key("item_id").eq(item_id),
        ScanIndexForward=False,
        Limit=50,
    )
    txns = txn_resp.get("Items", [])

    pending_orders = [
        {
            "timestamp": t.get("timestamp"),
            "quantity": int(float(t.get("quantity", 0))),
            "requested_by": t.get("dispensed_by"),
        }
        for t in txns if t.get("transaction_type") == "reorder_requested"
    ]

    last_restock = next(
        (t for t in txns if t.get("transaction_type") == "restocked"), None
    )

    return {
        "item_id": item_id,
        "item_name": item.get("item_name"),
        "supplier": item.get("supplier"),
        "lead_time_hours": int(float(item.get("lead_time_hours", 0))),
        "last_restocked": item.get("last_restocked"),
        "last_restock_quantity": int(float(last_restock.get("quantity", 0))) if last_restock else 0,
        "pending_orders": len(pending_orders),
        "pending_order_details": pending_orders,
    }
