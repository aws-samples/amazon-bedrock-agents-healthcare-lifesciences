"""Seed data handler - populates DynamoDB patients table on deployment."""

import os
import json
from decimal import Decimal

import boto3

from seed_data import PATIENTS

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))


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
    """Seed patient data into DynamoDB."""
    for patient in PATIENTS:
        item = convert_floats(patient)
        patients_table.put_item(Item=item)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"Seeded {len(PATIENTS)} patients"}),
    }
