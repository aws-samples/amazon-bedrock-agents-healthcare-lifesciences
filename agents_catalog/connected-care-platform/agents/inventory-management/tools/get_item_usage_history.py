"""Tool: Get usage/transaction history for an inventory item."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
transactions_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TRANSACTIONS_TABLE", "connected-care-inventory-transactions"))


@tool
def get_item_usage_history(item_id: str) -> dict:
    """Retrieve recent usage and restocking history for an inventory item.

    Args:
        item_id: The inventory item identifier (e.g., INV-001)

    Returns:
        List of recent transactions (dispensed, restocked) with timestamps and patient associations.
    """
    response = transactions_table.query(
        KeyConditionExpression=Key("item_id").eq(item_id),
        ScanIndexForward=False,
        Limit=20,
    )
    items = response.get("Items", [])

    if not items:
        return {"item_id": item_id, "transactions": [], "message": "No transaction history found"}

    transactions = []
    for txn in items:
        transactions.append({
            "timestamp": txn.get("timestamp"),
            "transaction_type": txn.get("transaction_type"),
            "quantity": int(float(txn.get("quantity", 0))),
            "floor": txn.get("floor"),
            "patient_id": txn.get("patient_id"),
            "dispensed_by": txn.get("dispensed_by"),
        })

    return {
        "item_id": item_id,
        "total_transactions": len(transactions),
        "transactions": transactions,
    }
