"""Tool: Create a planned field service dispatch."""

import os
import uuid
from datetime import datetime, timezone
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
visits_table = dynamodb.Table(os.environ.get("DYNAMODB_FIELD_SERVICE_VISITS_TABLE", "connected-care-field-service-visits"))


@tool
def create_service_dispatch(site_id: str, site_name: str, devices: str, engineer: str, parts_needed: str, priority: str, estimated_hours: int) -> dict:
    """Create a planned field service engineer dispatch to a hospital site.

    Args:
        site_id: Hospital site ID (e.g., site-002)
        site_name: Hospital name for display
        devices: Comma-separated device IDs to service (e.g., "D-8003,D-8005")
        engineer: FSE name to assign
        parts_needed: Comma-separated parts list
        priority: One of: routine, urgent, critical
        estimated_hours: Estimated visit duration in hours

    Returns:
        Dispatch confirmation with visit details.
    """
    visit_id = f"FSV-{uuid.uuid4().hex[:6].upper()}"
    device_list = [d.strip() for d in devices.split(",")]
    parts_list = [p.strip() for p in parts_needed.split(",")]

    visits_table.put_item(Item={
        "visit_id": visit_id,
        "site_id": site_id,
        "site_name": site_name,
        "engineer": engineer,
        "visit_date": "PLANNED",
        "devices_serviced": device_list,
        "visit_type": "planned",
        "duration_hours": estimated_hours,
        "parts_used": parts_list,
        "outcome": "scheduled",
        "notes": f"Priority: {priority}. Auto-dispatched by Field Service Agent.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "visit_id": visit_id,
        "site_id": site_id,
        "site_name": site_name,
        "engineer": engineer,
        "devices": device_list,
        "parts_needed": parts_list,
        "priority": priority,
        "estimated_hours": estimated_hours,
        "status": "scheduled",
        "message": f"Service dispatch {visit_id} created for {site_name}",
    }
