"""Tool: Get aggregate performance metrics for a device model across all sites."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))
sites_table = dynamodb.Table(os.environ.get("DYNAMODB_SITES_TABLE", "connected-care-sites"))


@tool
def get_device_performance_by_model(model: str) -> dict:
    """Get aggregate performance metrics for all instances of a device model across all hospital sites.

    Useful for quality teams to assess fleet-wide reliability and detect emerging issues.

    Args:
        model: Device model name (e.g., "BD Alaris 8015", "Hamilton C6", "Philips IntelliVue MX800")

    Returns:
        Fleet-wide performance summary with per-site breakdown.
    """
    devices_resp = devices_table.scan()
    matching = [d for d in devices_resp.get("Items", []) if d.get("model") == model]

    if not matching:
        return {"error": f"No devices found for model '{model}'"}

    for d in matching:
        if "site_id" not in d:
            d["site_id"] = "site-001"

    sites_resp = sites_table.scan()
    sites = {s["site_id"]: s for s in sites_resp.get("Items", [])}

    by_site = {}
    all_errors = []
    all_accuracy = []
    all_drift = []

    for device in matching:
        tel_resp = telemetry_table.query(
            KeyConditionExpression=Key("device_id").eq(device["device_id"]),
            ScanIndexForward=False, Limit=1,
        )
        telemetry = tel_resp["Items"][0].get("telemetry", {}) if tel_resp.get("Items") else {}

        errors = int(telemetry.get("error_count", 0))
        accuracy = float(telemetry.get("sensor_accuracy", 0))
        drift = float(telemetry.get("calibration_drift", 0))
        all_errors.append(errors)
        all_accuracy.append(accuracy)
        all_drift.append(drift)

        sid = device.get("site_id")
        site_info = sites.get(sid, {})
        site_name = site_info.get("site_name", "Unknown")

        if sid not in by_site:
            by_site[sid] = {"site_name": site_name, "city": site_info.get("city", ""), "devices": []}

        by_site[sid]["devices"].append({
            "device_id": device["device_id"],
            "firmware_version": device.get("firmware_version"),
            "risk_profile": device.get("risk_profile"),
            "error_count": errors,
            "sensor_accuracy": accuracy,
            "calibration_drift": drift,
            "uptime_hours": int(telemetry.get("uptime_hours", 0)),
        })

    n = len(matching)
    chart_data = []
    for sid, info in by_site.items():
        for d in info["devices"]:
            chart_data.append({
                "site_name": info["site_name"],
                "device_id": d["device_id"],
                "error_count": d["error_count"],
                "accuracy": d["sensor_accuracy"],
                "drift": d["calibration_drift"],
                "risk": d["risk_profile"],
            })

    return {
        "model": model,
        "total_devices": n,
        "total_sites": len(by_site),
        "fleet_avg_error_count": round(sum(all_errors) / n, 1),
        "fleet_avg_accuracy": round(sum(all_accuracy) / n, 1),
        "fleet_avg_drift": round(sum(all_drift) / n, 2),
        "sites": by_site,
        "chart_type": "model_performance",
        "chart_data": chart_data,
    }
