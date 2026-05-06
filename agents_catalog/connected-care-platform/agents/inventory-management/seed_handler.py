"""Seed data handler — populates DynamoDB inventory tables on deployment."""

import os
import json
from decimal import Decimal

import boto3

from seed_data import INVENTORY_ITEMS, INVENTORY_TRANSACTIONS

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
inventory_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory"))
transactions_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TRANSACTIONS_TABLE", "connected-care-inventory-transactions"))


def convert_floats(obj):
    """Convert float values to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj


def handler(event, context):
    """Seed inventory data and transaction history into DynamoDB."""
    for item in INVENTORY_ITEMS:
        inventory_table.put_item(Item=convert_floats(item))

    for txn in INVENTORY_TRANSACTIONS:
        item = convert_floats({
            "item_id": txn["item_id"],
            "timestamp": txn["timestamp"],
            "transaction_type": txn["transaction_type"],
            "quantity": txn["quantity"],
            "floor": txn["floor"],
            "patient_id": txn.get("patient_id"),
            "dispensed_by": txn.get("dispensed_by"),
        })
        transactions_table.put_item(Item=item)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Seeded {len(INVENTORY_ITEMS)} inventory items and {len(INVENTORY_TRANSACTIONS)} transactions"
        }),
    }
