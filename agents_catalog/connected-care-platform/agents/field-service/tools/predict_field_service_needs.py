"""Tool: Predict which devices need field service in the coming days."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))
sites_table = dynamodb.Table(os.environ.get("DYNAMODB_SITES_TABLE", "connected-care-sites"))

THRESHOLDS = {
    "battery_level": {"low": 20, "critical": 10},
    "sensor_accuracy": {"low": 90, "critical": 85},
    "error_count": {"high": 30, "critical": 50},
    "calibration_drift": {"high": 3.0, "critical": 5.0},
    "memory_usage": {"high": 80, "critical": 90},
}


@tool
def predict_field_service_needs(days_ahead: int = 14) -> dict:
    """Predict which devices across all sites will need field service within the specified timeframe.

    Evaluates telemetry against failure thresholds and firmware status.

    Args:
        days_ahead: Number of days to look ahead (default 14)

    Returns:
        Prioritized list of devices needing service, grouped by site.
    """
    sites_resp = sites_table.scan()
    sites = {s["site_id"]: s for s in sites_resp.get("Items", [])}

    devices_resp = devices_table.scan()
    all_devices = devices_resp.get("Items", [])
    for d in all_devices:
        if "site_id" not in d:
            d["site_id"] = "site-001"

    needs_service = []

    for device in all_devices:
        if device.get("status") != "active":
            continue

        tel_resp = telemetry_table.query(
            KeyConditionExpression=Key("device_id").eq(device["device_id"]),
            ScanIndexForward=False, Limit=1,
        )
        if not tel_resp.get("Items"):
            continue

        telemetry = tel_resp["Items"][0].get("telemetry", {})
        issues = []
        severity = "LOW"

        # Check thresholds
        battery = float(telemetry.get("battery_level", 100))
        if battery <= THRESHOLDS["battery_level"]["critical"]:
            issues.append(f"Battery critical: {battery}%")
            severity = "CRITICAL"
        elif battery <= THRESHOLDS["battery_level"]["low"]:
            issues.append(f"Battery low: {battery}%")
            severity = max(severity, "HIGH", key=lambda x: ["LOW", "MODERATE", "HIGH", "CRITICAL"].index(x))

        accuracy = float(telemetry.get("sensor_accuracy", 100))
        if accuracy <= THRESHOLDS["sensor_accuracy"]["critical"]:
            issues.append(f"Sensor accuracy critical: {accuracy}%")
            severity = "CRITICAL"
        elif accuracy <= THRESHOLDS["sensor_accuracy"]["low"]:
            issues.append(f"Sensor accuracy low: {accuracy}%")

        errors = int(telemetry.get("error_count", 0))
        if errors >= THRESHOLDS["error_count"]["critical"]:
            issues.append(f"Error count critical: {errors}")
            severity = "CRITICAL"
        elif errors >= THRESHOLDS["error_count"]["high"]:
            issues.append(f"Error count high: {errors}")

        drift = float(telemetry.get("calibration_drift", 0))
        if drift >= THRESHOLDS["calibration_drift"]["critical"]:
            issues.append(f"Calibration drift critical: {drift}%")
            severity = "CRITICAL"
        elif drift >= THRESHOLDS["calibration_drift"]["high"]:
            issues.append(f"Calibration drift high: {drift}%")

        # Check firmware
        if device.get("firmware_version") != device.get("latest_firmware"):
            issues.append(f"Firmware outdated: {device.get('firmware_version')} → {device.get('latest_firmware')}")

        if issues:
            sid = device.get("site_id", "unknown")
            site_info = sites.get(sid, {})
            needs_service.append({
                "device_id": device["device_id"],
                "site_id": sid,
                "site_name": site_info.get("site_name", "Unknown"),
                "city": site_info.get("city", ""),
                "model": device.get("model"),
                "device_type": device.get("device_type"),
                "location": device.get("location"),
                "severity": severity,
                "issues": issues,
                "last_maintenance": device.get("last_maintenance_date"),
            })

    # Sort by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    needs_service.sort(key=lambda x: severity_order.get(x["severity"], 4))

    chart_data = [
        {"site_name": d["site_name"], "device_id": d["device_id"], "model": d["model"], "severity": d["severity"], "issues_count": len(d["issues"])}
        for d in needs_service
    ]

    return {
        "days_ahead": days_ahead,
        "total_needing_service": len(needs_service),
        "critical_count": len([d for d in needs_service if d["severity"] == "CRITICAL"]),
        "devices": needs_service,
        "chart_type": "service_needs",
        "chart_data": chart_data,
    }
