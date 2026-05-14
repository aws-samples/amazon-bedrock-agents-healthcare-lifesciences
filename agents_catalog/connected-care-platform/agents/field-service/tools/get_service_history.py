"""Tool: Get field service visit history for a site or device."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
visits_table = dynamodb.Table(os.environ.get("DYNAMODB_FIELD_SERVICE_VISITS_TABLE", "connected-care-field-service-visits"))


@tool
def get_service_history(site_id: str = "", device_id: str = "") -> dict:
    """Get field service visit history for a hospital site or specific device.

    Args:
        site_id: Optional site filter (e.g., site-001)
        device_id: Optional device filter (e.g., D-4001)

    Returns:
        List of past FSE visits with details on devices serviced, parts used, and outcomes.
    """
    response = visits_table.scan()
    visits = response.get("Items", [])

    if site_id:
        visits = [v for v in visits if v.get("site_id") == site_id]
    if device_id:
        visits = [v for v in visits if device_id in v.get("devices_serviced", [])]

    visits.sort(key=lambda v: v.get("visit_date", ""), reverse=True)

    results = []
    for v in visits:
        results.append({
            "visit_id": v.get("visit_id"),
            "site_id": v.get("site_id"),
            "site_name": v.get("site_name"),
            "engineer": v.get("engineer"),
            "visit_date": v.get("visit_date"),
            "visit_type": v.get("visit_type"),
            "devices_serviced": v.get("devices_serviced", []),
            "duration_hours": int(float(v.get("duration_hours", 0))),
            "parts_used": v.get("parts_used", []),
            "outcome": v.get("outcome"),
            "notes": v.get("notes"),
        })

    return {
        "total_visits": len(results),
        "filter": {"site_id": site_id, "device_id": device_id},
        "visits": results,
    }
