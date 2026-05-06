"""Tool: List all devices assigned to a specific patient."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
assignments_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_ASSIGNMENTS_TABLE", "connected-care-device-assignments"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))


@tool
def get_devices_by_patient(patient_id: str) -> dict:
    """List all devices currently assigned to a specific patient.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        List of devices assigned to the patient with device details.
    """
    response = assignments_table.query(
        IndexName="patient-index",
        KeyConditionExpression=Key("patient_id").eq(patient_id),
    )

    assignments = response.get("Items", [])
    if not assignments:
        return {"patient_id": patient_id, "device_count": 0, "devices": [], "message": f"No devices assigned to patient {patient_id}"}

    devices = []
    for assignment in assignments:
        device_id = assignment["device_id"]
        device_resp = devices_table.get_item(Key={"device_id": device_id})
        device = device_resp.get("Item", {})
        devices.append({
            "device_id": device_id,
            "device_type": device.get("device_type"),
            "model": device.get("model"),
            "location": device.get("location"),
            "status": device.get("status"),
            "assigned_date": assignment.get("assigned_date"),
        })

    return {
        "patient_id": patient_id,
        "device_count": len(devices),
        "devices": devices,
    }
