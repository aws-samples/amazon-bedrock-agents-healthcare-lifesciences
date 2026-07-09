"""Tool: Get aggregate fleet health summary."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def get_fleet_summary() -> dict:
    """Get an aggregate fleet health summary with counts by status, type, and risk level.

    Returns:
        Fleet-wide summary including device counts by category and health distribution.
    """
    response = devices_table.scan()
    items = response.get("Items", [])

    by_status = {}
    by_type = {}
    by_risk = {}

    for item in items:
        status = item.get("status", "unknown")
        dtype = item.get("device_type", "unknown")
        risk = item.get("risk_profile", "unknown")

        by_status[status] = by_status.get(status, 0) + 1
        by_type[dtype] = by_type.get(dtype, 0) + 1
        by_risk[risk] = by_risk.get(risk, 0) + 1

    return {
        "total_devices": len(items),
        "by_status": by_status,
        "by_type": by_type,
        "by_risk_profile": by_risk,
    }
