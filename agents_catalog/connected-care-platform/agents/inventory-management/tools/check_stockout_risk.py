"""Tool: Assess stockout risk across all floors or a specific floor."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
inventory_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory"))


@tool
def check_stockout_risk(floor: str = "") -> dict:
    """Assess stockout risk for inventory items. Returns items sorted by urgency.

    Args:
        floor: Optional hospital floor filter (e.g., ICU, Floor1). If empty, checks all floors.

    Returns:
        Items at risk of stockout, sorted by hours until depletion, with patient impact counts.
    """
    if floor:
        response = inventory_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("floor").eq(floor)
        )
    else:
        response = inventory_table.scan()

    items = response.get("Items", [])
    at_risk = []

    for item in items:
        stock = float(item.get("current_stock", 0))
        burn_rate = float(item.get("burn_rate_per_hour", 0))
        hours_left = stock / burn_rate if burn_rate > 0 else 999

        if hours_left <= 24:
            if hours_left <= 4:
                risk = "CRITICAL"
            elif hours_left <= 12:
                risk = "HIGH"
            else:
                risk = "MODERATE"

            dependent = item.get("dependent_patients", [])
            subs = item.get("substitute_items", [])

            at_risk.append({
                "item_id": item.get("item_id"),
                "item_name": item.get("item_name"),
                "category": item.get("category"),
                "floor": item.get("floor"),
                "current_stock": int(stock),
                "unit": item.get("unit"),
                "burn_rate_per_hour": burn_rate,
                "hours_until_stockout": round(hours_left, 1),
                "stockout_risk": risk,
                "patients_affected": len(dependent),
                "dependent_patients": dependent,
                "has_substitutes": len(subs) > 0,
                "substitute_items": subs,
                "lead_time_hours": int(float(item.get("lead_time_hours", 0))),
            })

    at_risk.sort(key=lambda x: x["hours_until_stockout"])

    return {
        "floor_filter": floor or "ALL",
        "total_at_risk": len(at_risk),
        "critical_count": len([i for i in at_risk if i["stockout_risk"] == "CRITICAL"]),
        "high_count": len([i for i in at_risk if i["stockout_risk"] == "HIGH"]),
        "moderate_count": len([i for i in at_risk if i["stockout_risk"] == "MODERATE"]),
        "total_patients_affected": len(set(p for i in at_risk for p in i["dependent_patients"])),
        "items": at_risk,
    }
