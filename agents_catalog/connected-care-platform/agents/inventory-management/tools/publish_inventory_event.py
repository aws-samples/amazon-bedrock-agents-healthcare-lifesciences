"""Tool: Publish inventory events to EventBridge."""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool

eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))
EVENT_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")


@tool
def publish_inventory_event(
    item_id: str,
    event_type: str,
    severity: str,
    summary: str,
) -> dict:
    """Publish an inventory event to EventBridge for downstream workflow processing.

    Use this tool when you detect a stockout risk, critical shortage, or supply-related
    patient care impact.

    Args:
        item_id: The inventory item identifier (e.g., INV-001)
        event_type: One of: inventory.stockout_risk, inventory.stockout, inventory.reorder_created,
                    inventory.patient_impact, inventory.shortage_resolved
        severity: One of: LOW, MEDIUM, HIGH, CRITICAL
        summary: Brief summary of why this event is being published

    Returns:
        Confirmation that the event was published with the event ID.
    """
    valid_types = [
        "inventory.stockout_risk", "inventory.stockout", "inventory.reorder_created",
        "inventory.patient_impact", "inventory.shortage_resolved",
    ]
    if event_type not in valid_types:
        return {"error": f"Invalid event_type '{event_type}'. Must be one of: {valid_types}"}

    valid_severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if severity not in valid_severities:
        return {"error": f"Invalid severity '{severity}'. Must be one of: {valid_severities}"}

    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    event_detail = {
        "eventId": event_id,
        "timestamp": timestamp,
        "itemId": item_id,
        "severity": severity,
        "triggerSource": "AGENT",
        "payload": {
            "summary": summary,
            "agentName": "Inventory Management Agent",
        },
    }

    response = eventbridge.put_events(
        Entries=[
            {
                "Source": "inventory-management",
                "DetailType": event_type,
                "Detail": json.dumps(event_detail),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )

    failed = response.get("FailedEntryCount", 0)
    if failed > 0:
        return {"error": "Failed to publish event to EventBridge", "details": response}

    return {
        "event_id": event_id,
        "event_type": event_type,
        "item_id": item_id,
        "severity": severity,
        "timestamp": timestamp,
        "message": f"Inventory event '{event_type}' published successfully for item {item_id}",
    }
