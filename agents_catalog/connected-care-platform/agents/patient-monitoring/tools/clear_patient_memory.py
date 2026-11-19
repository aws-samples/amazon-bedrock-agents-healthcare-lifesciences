"""Tool: Clear patient memory on discharge — both DynamoDB timeline and AgentCore Memory."""

import os
import json
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
memory_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENT_MEMORY_TABLE", "connected-care-patient-memory"))

MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

try:
    agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)
except Exception:
    agentcore_client = None


def _clear_agentcore_memory(patient_id: str) -> dict:
    """Delete all AgentCore Memory long-term records for a patient."""
    if not MEMORY_ID or not agentcore_client:
        return {"cleared": False, "reason": "AgentCore Memory not configured"}

    deleted_count = 0
    try:
        namespace = f"/patient-{patient_id}/"
        # List all records in the patient's namespace
        response = agentcore_client.list_memory_records(
            memoryId=MEMORY_ID,
            namespace=namespace,
        )
        records = response.get("memoryRecordSummaries", [])

        # Delete each record
        for record in records:
            record_id = record.get("memoryRecordId")
            if record_id:
                try:
                    agentcore_client.delete_memory_record(
                        memoryId=MEMORY_ID,
                        memoryRecordId=record_id,
                    )
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete record {record_id}: {e}")

        return {"cleared": True, "records_deleted": deleted_count}

    except Exception as e:
        error_msg = str(e)
        # If namespace doesn't exist or no records, that's fine
        if "ResourceNotFoundException" in error_msg or "not found" in error_msg.lower():
            return {"cleared": True, "records_deleted": 0, "note": "No AgentCore Memory records found"}
        return {"cleared": False, "reason": error_msg}


@tool
def clear_patient_memory(patient_id: str) -> dict:
    """Clear all memory for a patient — both the DynamoDB timeline and AgentCore Memory
    long-term records. Generates a discharge summary before deletion.

    Use this on discharge or when resetting for a demo.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Discharge summary compiled from memory, and confirmation of deletion from both stores.
    """
    # Get DynamoDB timeline entries
    response = memory_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
        ScanIndexForward=True,
    )
    entries = response.get("Items", [])

    # Compile discharge summary before deletion
    summary_entries = []
    categories = {}
    for e in entries:
        summary_entries.append({
            "timestamp": e.get("timestamp"),
            "type": e.get("entry_type"),
            "category": e.get("category"),
            "summary": e.get("summary"),
            "recorded_by": e.get("recorded_by"),
        })
        cat = e.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    # Delete DynamoDB timeline entries
    ddb_deleted = 0
    for item in entries:
        memory_table.delete_item(Key={
            "patient_id": item["patient_id"],
            "timestamp": item["timestamp"],
        })
        ddb_deleted += 1

    # Delete AgentCore Memory long-term records
    agentcore_result = _clear_agentcore_memory(patient_id)

    return {
        "patient_id": patient_id,
        "status": "memory_cleared",
        "timeline_entries_deleted": ddb_deleted,
        "categories_cleared": categories,
        "agentcore_memory": agentcore_result,
        "discharge_summary": summary_entries,
        "message": f"Patient memory fully cleared for {patient_id}. Timeline: {ddb_deleted} entries deleted. AgentCore Memory: {agentcore_result.get('records_deleted', 0)} records deleted.",
    }
