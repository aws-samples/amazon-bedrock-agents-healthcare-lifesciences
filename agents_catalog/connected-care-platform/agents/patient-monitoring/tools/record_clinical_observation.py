"""Tool: Record a clinical observation to patient memory."""

import os
from datetime import datetime, timezone
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
memory_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENT_MEMORY_TABLE", "connected-care-patient-memory"))

MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

try:
    agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)
except Exception:
    agentcore_client = None


@tool
def record_clinical_observation(patient_id: str, observation: str, category: str, recorded_by: str = "clinician") -> dict:
    """Record a clinical observation to the patient's memory. Writes to both AgentCore Memory
    (for long-term semantic retrieval) and the timeline table (for sidebar display).

    Use this when a clinician reports something about a patient that should be remembered:
    medication responses, clinical changes, patient preferences, family interactions, etc.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        observation: Free-text clinical observation
        category: One of: medication_response, vitals_change, clinical_note, device_change, care_plan, family_update, discharge_planning
        recorded_by: Who recorded this (e.g., "RN Maria Santos", "Dr. Smith", "clinician")

    Returns:
        Confirmation that the observation was recorded to both memory stores.
    """
    valid_categories = [
        "medication_response", "vitals_change", "clinical_note",
        "device_change", "care_plan", "family_update", "discharge_planning",
    ]
    if category not in valid_categories:
        return {"error": f"Invalid category '{category}'. Must be one of: {valid_categories}"}

    now = datetime.now(timezone.utc).isoformat()

    # Write to DynamoDB timeline (sidebar display)
    memory_table.put_item(Item={
        "patient_id": patient_id,
        "timestamp": now,
        "entry_type": "observation",
        "category": category,
        "summary": observation,
        "details": "",
        "recorded_by": recorded_by,
        "active": "true",
    })

    # Write to AgentCore Memory (long-term semantic retrieval)
    agentcore_written = False
    if MEMORY_ID and agentcore_client:
        try:
            content = f"[{category.upper()}] Patient {patient_id} — {observation} (Recorded by: {recorded_by})"
            agentcore_client.write_memory_event(
                memoryId=MEMORY_ID,
                actorId=recorded_by,
                sessionId=f"patient-{patient_id}",
                eventContent={"conversationalEvent": {"conversationalMessages": [
                    {"role": "ASSISTANT", "content": content}
                ]}},
            )
            agentcore_written = True
        except Exception as e:
            print(f"AgentCore Memory write failed: {e}")

    return {
        "patient_id": patient_id,
        "category": category,
        "recorded_by": recorded_by,
        "timestamp": now,
        "agentcore_memory": agentcore_written,
        "message": f"Observation recorded for {patient_id}: {observation[:100]}. Written to AgentCore Memory: {agentcore_written}.",
    }
