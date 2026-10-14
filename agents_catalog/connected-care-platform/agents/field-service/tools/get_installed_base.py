"""Tool: Get installed base summary across all hospital sites."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
sites_table = dynamodb.Table(os.environ.get("DYNAMODB_SITES_TABLE", "connected-care-sites"))


@tool
def get_installed_base(site_id: str = "") -> dict:
    """Get the installed base of devices across all hospital sites or a specific site.

    Args:
        site_id: Optional site filter (e.g., site-001). If empty, returns all sites.

    Returns:
        Devices grouped by hospital site with risk distribution and firmware status.
    """
    sites_resp = sites_table.scan()
    sites = {s["site_id"]: s for s in sites_resp.get("Items", [])}

    devices_resp = devices_table.scan()
    all_devices = devices_resp.get("Items", [])

    # Assign site-001 to devices without site_id (existing Memorial General devices)
    for d in all_devices:
        if "site_id" not in d:
            d["site_id"] = "site-001"

    if site_id:
        all_devices = [d for d in all_devices if d.get("site_id") == site_id]

    by_site = {}
    for d in all_devices:
        sid = d.get("site_id", "unknown")
        if sid not in by_site:
            site_info = sites.get(sid, {})
            by_site[sid] = {
                "site_id": sid,
                "site_name": site_info.get("site_name", "Unknown"),
                "city": site_info.get("city", ""),
                "state": site_info.get("state", ""),
                "tier": site_info.get("tier", ""),
                "devices": [],
                "by_risk": {"critical": 0, "moderate": 0, "healthy": 0},
                "by_type": {},
            }
        risk = d.get("risk_profile", "unknown")
        if risk in by_site[sid]["by_risk"]:
            by_site[sid]["by_risk"][risk] += 1
        dtype = d.get("device_type", "unknown")
        by_site[sid]["by_type"][dtype] = by_site[sid]["by_type"].get(dtype, 0) + 1
        by_site[sid]["devices"].append({
            "device_id": d.get("device_id"),
            "device_type": dtype,
            "model": d.get("model"),
            "firmware_version": d.get("firmware_version"),
            "latest_firmware": d.get("latest_firmware"),
            "firmware_current": d.get("firmware_version") == d.get("latest_firmware"),
            "risk_profile": risk,
            "location": d.get("location"),
            "status": d.get("status"),
        })

    chart_data = []
    for sid, info in by_site.items():
        for d in info["devices"]:
            chart_data.append({
                "site_name": info["site_name"],
                "device_id": d["device_id"],
                "model": d["model"],
                "risk": d["risk_profile"],
                "firmware_current": d["firmware_current"],
                "device_type": d["device_type"],
            })

    return {
        "total_devices": len(all_devices),
        "total_sites": len(by_site),
        "sites": list(by_site.values()),
        "chart_type": "fleet_health",
        "chart_data": chart_data,
    }
