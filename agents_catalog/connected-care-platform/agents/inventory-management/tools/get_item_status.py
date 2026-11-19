"""Tool: Get detailed status for a specific inventory item."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
inventory_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory"))


@tool
def get_item_status(item_id: str) -> dict:
    """Retrieve detailed status for a specific inventory item including stock, burn rate, and patient dependencies.

    Args:
        item_id: The inventory item identifier (e.g., INV-001)

    Returns:
        Detailed item status with stockout risk assessment.
    """
    response = inventory_table.get_item(Key={"item_id": item_id})
    item = response.get("Item")
    if not item:
        return {"error": f"Item {item_id} not found"}

    stock = float(item.get("current_stock", 0))
    burn_rate = float(item.get("burn_rate_per_hour", 0))
    hours_left = stock / burn_rate if burn_rate > 0 else 999

    if hours_left <= 4:
        risk = "CRITICAL"
    elif hours_left <= 12:
        risk = "HIGH"
    elif hours_left <= 24:
        risk = "MODERATE"
    else:
        risk = "LOW"

    return {
        "item_id": item.get("item_id"),
        "item_name": item.get("item_name"),
        "category": item.get("category"),
        "floor": item.get("floor"),
        "storage_location": item.get("storage_location"),
        "current_stock": int(stock),
        "par_level": int(float(item.get("par_level", 0))),
        "unit": item.get("unit"),
        "burn_rate_per_hour": burn_rate,
        "hours_until_stockout": round(hours_left, 1),
        "stockout_risk": risk,
        "last_restocked": item.get("last_restocked"),
        "supplier": item.get("supplier"),
        "lead_time_hours": int(float(item.get("lead_time_hours", 0))),
        "substitute_items": item.get("substitute_items", []),
        "dependent_patients": item.get("dependent_patients", []),
        "notes": item.get("notes"),
    }
