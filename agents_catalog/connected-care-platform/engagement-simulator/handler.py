"""
Engagement Simulator — Lambda Handler

Generates medication adherence events and updates appointment statuses.
Triggered by CloudWatch Events schedule.
"""

import json
import os
import random
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
adherence_table = dynamodb.Table(os.environ.get("DYNAMODB_ADHERENCE_TABLE", "connected-care-medication-adherence"))

# Adherence profiles per patient
ADHERENCE_PROFILES = {
    "P-10001": {"rate": 0.80, "medications": ["MED-001", "MED-002", "MED-003", "MED-004"]},
    "P-10002": {"rate": 0.95, "medications": ["MED-005", "MED-006", "MED-007"]},
    "P-10003": {"rate": 0.60, "medications": ["MED-008", "MED-009"]},
    "P-10004": {"rate": 0.90, "medications": ["MED-010"]},
    "P-10005": {"rate": 0.95, "medications": ["MED-011", "MED-012"]},
}


def handler(event, context):
    """Generate medication adherence events for all patients."""
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    records = 0

    for patient_id, profile in ADHERENCE_PROFILES.items():
        for med_id in profile["medications"]:
            # Simulate whether dose was taken based on adherence rate
            roll = random.random()
            if roll < profile["rate"]:
                status = "taken"
            elif roll < profile["rate"] + 0.1:
                status = "late"
            else:
                status = "missed"

            adherence_table.put_item(Item={
                "patient_id": patient_id,
                "record_id": str(uuid.uuid4()),
                "medication_id": med_id,
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M"),
                "status": status,
                "timestamp": timestamp,
            })
            records += 1

    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"Generated {records} adherence records", "timestamp": timestamp}),
    }
