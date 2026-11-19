"""Seed data handler — populates DynamoDB devices table on deployment."""

import os
import json
from decimal import Decimal

import boto3

from seed_data import DEVICES, SMART_BED_TELEMETRY

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))


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
    """Seed device data and smart bed telemetry into DynamoDB."""
    for device in DEVICES:
        item = convert_floats(device)
        devices_table.put_item(Item=item)

    # Seed smart bed telemetry
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    for bed_data in SMART_BED_TELEMETRY:
        item = convert_floats({
            "device_id": bed_data["device_id"],
            "timestamp": now,
            "patient_id": bed_data.get("patient_id"),
            "telemetry": bed_data["telemetry"],
        })
        telemetry_table.put_item(Item=item)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"Seeded {len(DEVICES)} devices and {len(SMART_BED_TELEMETRY)} smart bed telemetry records"}),
    }
