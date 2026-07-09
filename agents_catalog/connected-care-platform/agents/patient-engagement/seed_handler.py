"""Seed data handler — populates DynamoDB engagement tables on deployment."""

import os
import json
from decimal import Decimal

import boto3

from seed_data import ENGAGEMENT_PROFILES, MEDICATIONS, APPOINTMENTS, MEDICATION_ADHERENCE, COMMUNICATION_LOG

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
profiles_table = dynamodb.Table(os.environ.get("DYNAMODB_ENGAGEMENT_PROFILES_TABLE", "connected-care-engagement-profiles"))
medications_table = dynamodb.Table(os.environ.get("DYNAMODB_MEDICATIONS_TABLE", "connected-care-medications"))
appointments_table = dynamodb.Table(os.environ.get("DYNAMODB_APPOINTMENTS_TABLE", "connected-care-appointments"))
adherence_table = dynamodb.Table(os.environ.get("DYNAMODB_ADHERENCE_TABLE", "connected-care-medication-adherence"))
comms_table = dynamodb.Table(os.environ.get("DYNAMODB_COMMUNICATIONS_TABLE", "connected-care-communications"))


def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj


def handler(event, context):
    counts = {}
    for p in ENGAGEMENT_PROFILES:
        profiles_table.put_item(Item=convert_floats(p))
    counts["profiles"] = len(ENGAGEMENT_PROFILES)

    for m in MEDICATIONS:
        medications_table.put_item(Item=convert_floats(m))
    counts["medications"] = len(MEDICATIONS)

    for a in APPOINTMENTS:
        appointments_table.put_item(Item=convert_floats(a))
    counts["appointments"] = len(APPOINTMENTS)

    for ad in MEDICATION_ADHERENCE:
        adherence_table.put_item(Item=convert_floats(ad))
    counts["adherence_records"] = len(MEDICATION_ADHERENCE)

    for c in COMMUNICATION_LOG:
        comms_table.put_item(Item=convert_floats(c))
    counts["communication_logs"] = len(COMMUNICATION_LOG)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Engagement data seeded", "counts": counts}),
    }
