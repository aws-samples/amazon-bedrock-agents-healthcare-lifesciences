"""Tool: Assign a device to a patient."""

import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
assignments_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_ASSIGNMENTS_TABLE", "connected-care-device-assignments"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def assign_device_to_patient(device_id: str, patient_id: str) -> dict:
    """Assign a device to a patient. Creates a device-patient mapping.

    Args:
        device_id: The device identifier (e.g., D-2001)
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Confirmation of the assignment with assignment details.
    """
    # Verify device exists
    device_resp = devices_table.get_item(Key={"device_id": device_id})
    if not device_resp.get("Item"):
        return {"error": f"Device {device_id} not found"}

    # Check if device is already assigned
    existing = assignments_table.get_item(Key={"device_id": device_id})
    if existing.get("Item"):
        existing_patient = existing["Item"].get("patient_id")
        return {"error": f"Device {device_id} is already assigned to patient {existing_patient}. Unassign it first."}

    assignment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    assignments_table.put_item(Item={
        "device_id": device_id,
        "patient_id": patient_id,
        "assignment_id": assignment_id,
        "assigned_date": now,
    })

    return {
        "assignment_id": assignment_id,
        "device_id": device_id,
        "patient_id": patient_id,
        "assigned_date": now,
        "message": f"Device {device_id} successfully assigned to patient {patient_id}",
    }
