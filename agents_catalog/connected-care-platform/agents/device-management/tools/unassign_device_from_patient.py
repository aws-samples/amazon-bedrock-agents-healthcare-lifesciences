"""Tool: Remove a device-patient assignment."""

import os
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
assignments_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_ASSIGNMENTS_TABLE", "connected-care-device-assignments"))


@tool
def unassign_device_from_patient(device_id: str) -> dict:
    """Remove a device from its current patient assignment.

    Args:
        device_id: The device identifier (e.g., D-2001)

    Returns:
        Confirmation that the assignment was removed.
    """
    existing = assignments_table.get_item(Key={"device_id": device_id})
    if not existing.get("Item"):
        return {"error": f"Device {device_id} is not currently assigned to any patient"}

    patient_id = existing["Item"].get("patient_id")
    assignments_table.delete_item(Key={"device_id": device_id})

    return {
        "device_id": device_id,
        "previous_patient_id": patient_id,
        "message": f"Device {device_id} unassigned from patient {patient_id}",
    }
