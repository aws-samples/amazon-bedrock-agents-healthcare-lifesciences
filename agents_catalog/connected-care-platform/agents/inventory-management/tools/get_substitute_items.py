"""Tool: Find substitute items for a supply that is low or out of stock."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
inventory_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory"))


@tool
def get_substitute_items(item_id: str) -> dict:
    """Find available substitutes for a low-stock or out-of-stock inventory item.

    Checks if substitute items are available on the same floor or other floors.

    Args:
        item_id: The inventory item identifier (e.g., INV-001)

    Returns:
        List of substitute items with their availability across floors.
    """
    inv_resp = inventory_table.get_item(Key={"item_id": item_id})
    item = inv_resp.get("Item")
    if not item:
        return {"error": f"Item {item_id} not found"}

    sub_names = item.get("substitute_items", [])
    if not sub_names:
        return {
            "item_id": item_id,
            "item_name": item.get("item_name"),
            "substitutes_available": False,
            "substitutes": [],
            "message": "No known substitutes for this item. Physician consultation required.",
        }

    # Scan for items matching substitute names across all floors
    all_items = inventory_table.scan().get("Items", [])
    substitutes = []
    for inv in all_items:
        if inv.get("item_name") in sub_names:
            stock = float(inv.get("current_stock", 0))
            burn_rate = float(inv.get("burn_rate_per_hour", 0))
            hours_left = stock / burn_rate if burn_rate > 0 else 999
            substitutes.append({
                "item_id": inv.get("item_id"),
                "item_name": inv.get("item_name"),
                "floor": inv.get("floor"),
                "current_stock": int(stock),
                "unit": inv.get("unit"),
                "hours_until_stockout": round(hours_left, 1),
                "storage_location": inv.get("storage_location"),
            })

    return {
        "item_id": item_id,
        "item_name": item.get("item_name"),
        "floor": item.get("floor"),
        "substitutes_available": len(substitutes) > 0,
        "substitutes": substitutes,
    }
