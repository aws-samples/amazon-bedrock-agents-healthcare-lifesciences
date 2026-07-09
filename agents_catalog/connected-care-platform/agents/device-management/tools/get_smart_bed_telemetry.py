"""Tool: Get current smart bed telemetry including pressure zones, repositioning, and bed exit data."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))


@tool
def get_smart_bed_telemetry(identifier: str) -> dict:
    """Retrieve current smart bed telemetry including pressure zones, repositioning history,
    bed exit events, Braden score, and head-of-bed angle.

    Can look up by device_id (e.g., D-7001) or patient_id (e.g., P-10001).

    Args:
        identifier: Either a device ID (D-7xxx) or patient ID (P-1xxxx)

    Returns:
        Smart bed telemetry with pressure zones, repositioning data, Braden score,
        and bed exit information.
    """
    device_id = identifier

    # If patient ID provided, find the smart bed assigned to that patient
    if identifier.startswith("P-"):
        scan_resp = devices_table.scan(
            FilterExpression="device_type = :dt AND assigned_patient_id = :pid",
            ExpressionAttributeValues={":dt": "smart_bed", ":pid": identifier},
        )
        items = scan_resp.get("Items", [])
        if not items:
            return {"error": f"No smart bed found for patient {identifier}"}
        device_id = items[0]["device_id"]

    # Get device profile
    device_resp = devices_table.get_item(Key={"device_id": device_id})
    device = device_resp.get("Item")
    if not device:
        return {"error": f"Device {device_id} not found"}
    if device.get("device_type") != "smart_bed":
        return {"error": f"Device {device_id} is not a smart bed (type: {device.get('device_type')})"}

    # Get latest telemetry
    telemetry_resp = telemetry_table.query(
        KeyConditionExpression=Key("device_id").eq(device_id),
        ScanIndexForward=False,
        Limit=1,
    )

    if not telemetry_resp.get("Items"):
        return {"error": f"No telemetry data available for smart bed {device_id}"}

    item = telemetry_resp["Items"][0]
    t = item.get("telemetry", {})

    # Build pressure zone summary
    pressure_zones = t.get("pressure_zones", {})
    high_pressure_zones = [
        {"zone": zone, **data}
        for zone, data in pressure_zones.items()
        if data.get("status") in ("high", "elevated")
    ]

    braden = t.get("braden_score", {})

    return {
        "device_id": device_id,
        "patient_id": item.get("patient_id") or device.get("assigned_patient_id"),
        "model": device.get("model"),
        "location": device.get("location"),
        "timestamp": item.get("timestamp"),
        "bed_position": t.get("bed_position"),
        "head_of_bed_angle": float(t.get("head_of_bed_angle", 0)),
        "rail_status": t.get("rail_status"),
        "bed_exit_alarm": t.get("bed_exit_alarm"),
        "last_bed_exit": t.get("last_bed_exit"),
        "last_repositioned": t.get("last_repositioned"),
        "hours_since_reposition": float(t.get("hours_since_reposition", 0)),
        "restlessness_score": float(t.get("restlessness_score", 0)),
        "weight_kg": float(t.get("weight_kg", 0)),
        "pressure_zones": {zone: {
            "pressure_mmhg": float(data.get("pressure_mmhg", 0)),
            "duration_minutes": int(data.get("duration_minutes", 0)),
            "status": data.get("status"),
        } for zone, data in pressure_zones.items()},
        "high_pressure_zones": high_pressure_zones,
        "braden_score_total": int(braden.get("total", 0)),
        "braden_risk_level": braden.get("risk_level", "UNKNOWN"),
        "braden_subscores": {
            "sensory_perception": int(braden.get("sensory_perception", 0)),
            "moisture": int(braden.get("moisture", 0)),
            "activity": int(braden.get("activity", 0)),
            "mobility": int(braden.get("mobility", 0)),
            "nutrition": int(braden.get("nutrition", 0)),
            "friction_shear": int(braden.get("friction_shear", 0)),
        },
        "repositioning_overdue": float(t.get("hours_since_reposition", 0)) > 2.0,
        "battery_level": float(t.get("battery_level", 0)),
        "connectivity_status": t.get("connectivity_status"),
    }
