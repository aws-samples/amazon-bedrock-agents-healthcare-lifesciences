"""Tool: Identify patients affected by a specific supply shortage."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
inventory_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))


@tool
def get_patients_affected_by_shortage(item_id: str) -> dict:
    """Identify which patients are affected by a shortage of a specific inventory item.

    Cross-references the item's dependent patients with patient records to provide
    clinical context about the impact.

    Args:
        item_id: The inventory item identifier (e.g., INV-001)

    Returns:
        List of affected patients with their clinical context and urgency assessment.
    """
    inv_resp = inventory_table.get_item(Key={"item_id": item_id})
    item = inv_resp.get("Item")
    if not item:
        return {"error": f"Item {item_id} not found"}

    dependent_ids = item.get("dependent_patients", [])
    if not dependent_ids:
        return {
            "item_id": item_id,
            "item_name": item.get("item_name"),
            "patients_affected": 0,
            "patients": [],
            "message": "No patients currently depend on this item",
        }

    stock = float(item.get("current_stock", 0))
    burn_rate = float(item.get("burn_rate_per_hour", 0))
    hours_left = stock / burn_rate if burn_rate > 0 else 999
    subs = item.get("substitute_items", [])

    affected = []
    for pid in dependent_ids:
        patient_resp = patients_table.get_item(Key={"patient_id": pid})
        patient = patient_resp.get("Item")
        if patient:
            affected.append({
                "patient_id": pid,
                "name": patient.get("name"),
                "room": patient.get("room"),
                "risk_profile": patient.get("risk_profile"),
                "conditions": patient.get("conditions", []),
                "relevant_medications": [
                    m for m in patient.get("medications", [])
                    if item.get("item_name", "").split()[0].lower() in m.get("name", "").lower()
                ],
            })
        else:
            affected.append({
                "patient_id": pid,
                "name": "Unknown",
                "room": "Unknown",
                "risk_profile": "unknown",
                "conditions": [],
                "relevant_medications": [],
            })

    return {
        "item_id": item_id,
        "item_name": item.get("item_name"),
        "floor": item.get("floor"),
        "current_stock": int(stock),
        "hours_until_stockout": round(hours_left, 1),
        "substitute_available": len(subs) > 0,
        "substitutes": subs,
        "patients_affected": len(affected),
        "patients": affected,
    }
