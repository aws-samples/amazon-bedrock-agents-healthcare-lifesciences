"""Seed nurse assignments, alert history, and workload data into DynamoDB.

Run after deploying ConnectedCareAgentCoreStack:
  python scripts/seed-nurse-data.py
"""

import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))

import boto3
from nurse_seed_data import NURSE_ASSIGNMENTS, ALERT_HISTORY, NURSE_WORKLOAD

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

assignments_table = dynamodb.Table("connected-care-nurse-assignments")
alert_history_table = dynamodb.Table("connected-care-alert-history")
workload_table = dynamodb.Table("connected-care-nurse-workload")


def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj


def seed():
    print("Seeding nurse assignments...")
    for item in NURSE_ASSIGNMENTS:
        assignments_table.put_item(Item=convert_floats(item))
    print(f"  {len(NURSE_ASSIGNMENTS)} nurse assignments seeded")

    print("Seeding alert history...")
    for item in ALERT_HISTORY:
        alert_history_table.put_item(Item=convert_floats(item))
    print(f"  {len(ALERT_HISTORY)} alert history records seeded")

    print("Seeding nurse workload...")
    for item in NURSE_WORKLOAD:
        workload_table.put_item(Item=convert_floats(item))
    print(f"  {len(NURSE_WORKLOAD)} workload records seeded")

    print("\nDone! Nurse alert fatigue data is ready.")


if __name__ == "__main__":
    seed()
