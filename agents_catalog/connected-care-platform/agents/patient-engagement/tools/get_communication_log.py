"""Tool: Get past notifications and messages sent to a patient."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
communications_table = dynamodb.Table(os.environ.get("DYNAMODB_COMMUNICATIONS_TABLE", "connected-care-communications"))


@tool
def get_communication_log(patient_id: str) -> dict:
    """Retrieve the communication log for a patient.

    Returns all past notifications, reminders, and messages sent to the patient.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        List of communication records with channel, type, content, and delivery status.
    """
    response = communications_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
    )

    items = response.get("Items", [])
    if not items:
        return {"error": f"No communication records found for patient {patient_id}"}

    records = []
    for log in items:
        records.append({
            "log_id": log.get("log_id"),
            "timestamp": log.get("timestamp"),
            "channel": log.get("channel"),
            "type": log.get("type"),
            "content": log.get("content"),
            "status": log.get("status"),
        })

    return sanitize({
        "patient_id": patient_id,
        "total_communications": len(records),
        "records": records,
    })
