"""Tool: Find all devices in a room or floor and their status."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))


@tool
def check_nearby_sensors(location: str) -> dict:
    """Find all devices in a specific room or floor and their current status.

    Useful for fall investigation (corroborating sensor data) and device failure
    impact assessment (finding replacement devices nearby).

    Args:
        location: Room identifier (e.g., ICU-412) or floor (e.g., Floor1, ICU)

    Returns:
        List of devices at the specified location with their latest telemetry.
    """
    # Scan for devices matching location or floor
    response = devices_table.scan()
    items = response.get("Items", [])

    matching = []
    for item in items:
        device_location = item.get("location", "")
        device_floor = item.get("floor", "")
        if location.lower() in device_location.lower() or location.lower() in device_floor.lower():
            # Get latest telemetry
            tel_resp = telemetry_table.query(
                KeyConditionExpression=Key("device_id").eq(item["device_id"]),
                ScanIndexForward=False,
                Limit=1,
            )
            telemetry = {}
            if tel_resp.get("Items"):
                telemetry = tel_resp["Items"][0].get("telemetry", {})

            matching.append({
                "device_id": item["device_id"],
                "device_type": item.get("device_type"),
                "model": item.get("model"),
                "location": device_location,
                "status": item.get("status"),
                "risk_profile": item.get("risk_profile"),
                "battery_level": float(telemetry.get("battery_level", 0)),
                "connectivity_status": telemetry.get("connectivity_status", "unknown"),
                "sensor_accuracy": float(telemetry.get("sensor_accuracy", 0)),
            })

    if not matching:
        return {"location": location, "device_count": 0, "devices": [], "message": f"No devices found at location '{location}'"}

    return {
        "location": location,
        "device_count": len(matching),
        "devices": matching,
    }
