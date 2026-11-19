"""Tool: Compare device performance across firmware versions."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))
sites_table = dynamodb.Table(os.environ.get("DYNAMODB_SITES_TABLE", "connected-care-sites"))


@tool
def compare_firmware_performance(model: str) -> dict:
    """Compare telemetry performance across firmware versions for a specific device model.

    Useful for identifying firmware-related quality issues and prioritizing upgrades.

    Args:
        model: Device model name (e.g., "BD Alaris 8015", "Hamilton C6")

    Returns:
        Performance metrics grouped by firmware version with upgrade recommendations.
    """
    devices_resp = devices_table.scan()
    all_devices = [d for d in devices_resp.get("Items", []) if d.get("model") == model]

    if not all_devices:
        return {"error": f"No devices found for model '{model}'"}

    for d in all_devices:
        if "site_id" not in d:
            d["site_id"] = "site-001"

    sites_resp = sites_table.scan()
    sites = {s["site_id"]: s for s in sites_resp.get("Items", [])}

    by_firmware = {}
    for device in all_devices:
        fw = device.get("firmware_version", "unknown")
        if fw not in by_firmware:
            by_firmware[fw] = {"firmware": fw, "devices": [], "error_counts": [], "accuracy": [], "drift": [], "is_latest": fw == device.get("latest_firmware")}

        tel_resp = telemetry_table.query(
            KeyConditionExpression=Key("device_id").eq(device["device_id"]),
            ScanIndexForward=False, Limit=1,
        )
        telemetry = tel_resp["Items"][0].get("telemetry", {}) if tel_resp.get("Items") else {}

        sid = device.get("site_id", "unknown")
        site_info = sites.get(sid, {})
        by_firmware[fw]["devices"].append({
            "device_id": device["device_id"],
            "site_name": site_info.get("site_name", "Unknown"),
            "risk_profile": device.get("risk_profile"),
        })
        by_firmware[fw]["error_counts"].append(int(telemetry.get("error_count", 0)))
        by_firmware[fw]["accuracy"].append(float(telemetry.get("sensor_accuracy", 0)))
        by_firmware[fw]["drift"].append(float(telemetry.get("calibration_drift", 0)))

    results = []
    chart_data = []
    for fw, data in sorted(by_firmware.items()):
        n = len(data["devices"])
        avg_errors = sum(data["error_counts"]) / n if n else 0
        avg_accuracy = sum(data["accuracy"]) / n if n else 0
        avg_drift = sum(data["drift"]) / n if n else 0

        if data["is_latest"]:
            recommendation = "CURRENT — no action"
        elif avg_errors > 50:
            recommendation = "UPGRADE IMMEDIATELY"
        elif avg_errors > 20:
            recommendation = "UPGRADE RECOMMENDED"
        else:
            recommendation = "UPGRADE WHEN CONVENIENT"

        results.append({
            "firmware_version": fw,
            "device_count": n,
            "is_latest": data["is_latest"],
            "avg_error_count": round(avg_errors, 1),
            "avg_sensor_accuracy": round(avg_accuracy, 1),
            "avg_calibration_drift": round(avg_drift, 2),
            "recommendation": recommendation,
            "devices": data["devices"],
        })
        chart_data.append({
            "firmware": fw,
            "devices": n,
            "avg_errors": round(avg_errors, 1),
            "avg_accuracy": round(avg_accuracy, 1),
            "is_latest": data["is_latest"],
        })

    return {
        "model": model,
        "total_devices": len(all_devices),
        "firmware_versions": len(results),
        "versions": results,
        "chart_type": "firmware_comparison",
        "chart_data": chart_data,
    }
