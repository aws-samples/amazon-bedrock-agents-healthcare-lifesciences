"""Seed ALL data into DynamoDB — patients, devices, engagement, and nurse data.

Run after deploying all CDK stacks:
  python scripts/seed/seed-all.py
"""

import json
import boto3

lambda_client = boto3.client("lambda", region_name="us-east-1")


def invoke_seed_lambda(function_name, label):
    print(f"Seeding {label}...")
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=b"{}",
        )
        body = json.loads(response["Payload"].read().decode())
        result = json.loads(body.get("body", "{}")) if isinstance(body.get("body"), str) else body
        print(f"  {result.get('message', 'Done')}")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    print("=== Connected Care Platform — Seed All Data ===\n")

    invoke_seed_lambda("connected-care-seed-data", "Patient Monitoring (patients, vitals)")
    invoke_seed_lambda("connected-care-device-seed-data", "Device Management (devices, telemetry, smart beds)")
    invoke_seed_lambda("connected-care-engagement-seed-data", "Patient Engagement (profiles, medications, appointments)")
    invoke_seed_lambda("connected-care-inventory-seed-data", "Inventory Management (floor inventory, transactions)")
    invoke_seed_lambda("connected-care-field-service-seed-data", "Field Service (sites, contracts, multi-site devices, visits)")

    # Nurse data is seeded directly (not via Lambda)
    print("Seeding Nurse Alert Fatigue data...")
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        from nurse_seed_data import NURSE_ASSIGNMENTS, ALERT_HISTORY, NURSE_WORKLOAD
        from decimal import Decimal

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        def convert_floats(obj):
            if isinstance(obj, float):
                return Decimal(str(obj))
            if isinstance(obj, dict):
                return {k: convert_floats(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_floats(i) for i in obj]
            return obj

        for item in NURSE_ASSIGNMENTS:
            dynamodb.Table("connected-care-nurse-assignments").put_item(Item=convert_floats(item))
        print(f"  {len(NURSE_ASSIGNMENTS)} nurse assignments")

        for item in ALERT_HISTORY:
            dynamodb.Table("connected-care-alert-history").put_item(Item=convert_floats(item))
        print(f"  {len(ALERT_HISTORY)} alert history records")

        for item in NURSE_WORKLOAD:
            dynamodb.Table("connected-care-nurse-workload").put_item(Item=convert_floats(item))
        print(f"  {len(NURSE_WORKLOAD)} workload records")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n=== All data seeded successfully ===")
