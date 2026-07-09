"""
Vital Sign Data Simulator - Lambda Handler

Generates realistic synthetic vital sign data for 5 simulated patients
and writes to DynamoDB. Triggered automatically by CloudWatch Events schedule.
"""

import json
import os
import random
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))
vitals_table = dynamodb.Table(os.environ.get("DYNAMODB_VITALS_TABLE", "connected-care-vitals"))


# Patient simulation profiles define how vitals behave
SIMULATION_PROFILES = {
    "P-10001": {  # Margaret Chen - Critical (deteriorating)
        "risk_profile": "critical",
        "heart_rate": {"base": 98, "drift": 0.3, "noise": 4},
        "blood_pressure_systolic": {"base": 88, "drift": -0.2, "noise": 5},
        "blood_pressure_diastolic": {"base": 55, "drift": -0.1, "noise": 3},
        "temperature": {"base": 100.2, "drift": 0.05, "noise": 0.3},
        "spo2": {"base": 91, "drift": -0.1, "noise": 1},
        "respiratory_rate": {"base": 24, "drift": 0.15, "noise": 2},
        "blood_glucose": {"base": 210, "drift": 0.5, "noise": 15},
    },
    "P-10002": {  # James Rodriguez - Moderate
        "risk_profile": "moderate",
        "heart_rate": {"base": 82, "drift": 0.0, "noise": 5},
        "blood_pressure_systolic": {"base": 138, "drift": 0.0, "noise": 8},
        "blood_pressure_diastolic": {"base": 85, "drift": 0.0, "noise": 4},
        "temperature": {"base": 98.8, "drift": 0.0, "noise": 0.3},
        "spo2": {"base": 95, "drift": 0.0, "noise": 1},
        "respiratory_rate": {"base": 18, "drift": 0.0, "noise": 2},
        "blood_glucose": {"base": 125, "drift": 0.0, "noise": 10},
    },
    "P-10003": {  # Aisha Patel - Moderate
        "risk_profile": "moderate",
        "heart_rate": {"base": 76, "drift": 0.0, "noise": 4},
        "blood_pressure_systolic": {"base": 122, "drift": 0.0, "noise": 6},
        "blood_pressure_diastolic": {"base": 78, "drift": 0.0, "noise": 3},
        "temperature": {"base": 98.4, "drift": 0.0, "noise": 0.2},
        "spo2": {"base": 94, "drift": 0.0, "noise": 1.5},
        "respiratory_rate": {"base": 19, "drift": 0.0, "noise": 2},
        "blood_glucose": {"base": 185, "drift": 0.0, "noise": 30},
    },
    "P-10004": {  # Robert Kim - Stable
        "risk_profile": "stable",
        "heart_rate": {"base": 72, "drift": 0.0, "noise": 3},
        "blood_pressure_systolic": {"base": 118, "drift": 0.0, "noise": 5},
        "blood_pressure_diastolic": {"base": 75, "drift": 0.0, "noise": 3},
        "temperature": {"base": 98.6, "drift": 0.0, "noise": 0.2},
        "spo2": {"base": 98, "drift": 0.0, "noise": 0.5},
        "respiratory_rate": {"base": 15, "drift": 0.0, "noise": 1},
        "blood_glucose": {"base": 95, "drift": 0.0, "noise": 8},
    },
    "P-10005": {  # Linda Okafor - Stable
        "risk_profile": "stable",
        "heart_rate": {"base": 68, "drift": 0.0, "noise": 3},
        "blood_pressure_systolic": {"base": 115, "drift": 0.0, "noise": 4},
        "blood_pressure_diastolic": {"base": 72, "drift": 0.0, "noise": 3},
        "temperature": {"base": 99.1, "drift": -0.01, "noise": 0.3},
        "spo2": {"base": 96, "drift": 0.0, "noise": 1},
        "respiratory_rate": {"base": 17, "drift": 0.0, "noise": 1.5},
        "blood_glucose": {"base": 100, "drift": 0.0, "noise": 6},
    },
}


def generate_vital(profile: dict, vital_name: str) -> Decimal:
    """Generate a single vital sign reading with drift and noise."""
    cfg = profile[vital_name]
    value = cfg["base"] + cfg["drift"] + random.gauss(0, cfg["noise"])

    # Update drift for next reading (critical patients trend over time)
    cfg["base"] = cfg["base"] + cfg["drift"]

    # Clamp to physiologically plausible ranges
    clamps = {
        "heart_rate": (30, 200),
        "blood_pressure_systolic": (60, 220),
        "blood_pressure_diastolic": (30, 140),
        "temperature": (93.0, 108.0),
        "spo2": (70, 100),
        "respiratory_rate": (5, 45),
        "blood_glucose": (30, 500),
    }
    low, high = clamps.get(vital_name, (0, 9999))
    value = max(low, min(high, value))

    # Round appropriately
    if vital_name in ("temperature",):
        return Decimal(str(round(value, 1)))
    return Decimal(str(round(value)))


def handler(event, context):
    """Lambda handler - generates vitals for all patients and writes to DynamoDB."""
    timestamp = datetime.now(timezone.utc).isoformat()
    records_written = 0

    for patient_id, profile in SIMULATION_PROFILES.items():
        vitals = {}
        for vital_name in [
            "heart_rate",
            "blood_pressure_systolic",
            "blood_pressure_diastolic",
            "temperature",
            "spo2",
            "respiratory_rate",
            "blood_glucose",
        ]:
            vitals[vital_name] = generate_vital(profile, vital_name)

        # Write to DynamoDB vitals table
        item = {
            "patient_id": patient_id,
            "timestamp": timestamp,
            "reading_id": str(uuid.uuid4()),
            "vitals": vitals,
            "risk_profile": profile["risk_profile"],
        }

        vitals_table.put_item(Item=item)
        records_written += 1

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Generated vitals for {records_written} patients",
            "timestamp": timestamp,
        }),
    }
