"""Tool: Get current inventory levels for a hospital floor."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
inventory_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory"))


@tool
def get_floor_inventory(floor: str) -> dict:
    """Retrieve all inventory items and their current stock levels for a specific hospital floor.

    Args:
        floor: The hospital floor (e.g., ICU, Floor1, Floor2, Floor3)

    Returns:
        List of inventory items with stock levels, par levels, burn rates, and risk assessment.
    """
    response = inventory_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("floor").eq(floor)
    )
    items = response.get("Items", [])

    if not items:
        return {"error": f"No inventory data found for floor {floor}"}

    result = []
    for item in items:
        stock = float(item.get("current_stock", 0))
        par = float(item.get("par_level", 1))
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

        result.append({
            "item_id": item.get("item_id"),
            "item_name": item.get("item_name"),
            "category": item.get("category"),
            "current_stock": int(stock),
            "par_level": int(par),
            "unit": item.get("unit"),
            "burn_rate_per_hour": burn_rate,
            "hours_until_stockout": round(hours_left, 1),
            "stockout_risk": risk,
            "storage_location": item.get("storage_location"),
            "dependent_patients": item.get("dependent_patients", []),
        })

    result.sort(key=lambda x: x["hours_until_stockout"])

    return {
        "floor": floor,
        "total_items": len(result),
        "critical_items": len([i for i in result if i["stockout_risk"] == "CRITICAL"]),
        "high_risk_items": len([i for i in result if i["stockout_risk"] == "HIGH"]),
        "items": result,
    }
