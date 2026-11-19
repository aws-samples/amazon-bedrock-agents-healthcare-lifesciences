"""Seed data handler — populates multi-site, service contract, and field visit tables."""

import os
import json
from decimal import Decimal
from datetime import datetime, timezone

import boto3

from seed_data import SITES, SERVICE_CONTRACTS, MULTI_SITE_DEVICES, MULTI_SITE_TELEMETRY, FIELD_SERVICE_VISITS

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
sites_table = dynamodb.Table(os.environ.get("DYNAMODB_SITES_TABLE", "connected-care-sites"))
contracts_table = dynamodb.Table(os.environ.get("DYNAMODB_SERVICE_CONTRACTS_TABLE", "connected-care-service-contracts"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))
visits_table = dynamodb.Table(os.environ.get("DYNAMODB_FIELD_SERVICE_VISITS_TABLE", "connected-care-field-service-visits"))


def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj


def handler(event, context):
    """Seed multi-site data into DynamoDB."""
    for site in SITES:
        sites_table.put_item(Item=convert_floats(site))

    for contract in SERVICE_CONTRACTS:
        contracts_table.put_item(Item=convert_floats(contract))

    for device in MULTI_SITE_DEVICES:
        devices_table.put_item(Item=convert_floats(device))

    now = datetime.now(timezone.utc).isoformat()
    for tel in MULTI_SITE_TELEMETRY:
        telemetry_table.put_item(Item=convert_floats({
            "device_id": tel["device_id"],
            "timestamp": now,
            "telemetry": tel["telemetry"],
        }))

    for visit in FIELD_SERVICE_VISITS:
        visits_table.put_item(Item=convert_floats(visit))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Seeded {len(SITES)} sites, {len(SERVICE_CONTRACTS)} contracts, {len(MULTI_SITE_DEVICES)} devices, {len(MULTI_SITE_TELEMETRY)} telemetry records, {len(FIELD_SERVICE_VISITS)} visits"
        }),
    }
