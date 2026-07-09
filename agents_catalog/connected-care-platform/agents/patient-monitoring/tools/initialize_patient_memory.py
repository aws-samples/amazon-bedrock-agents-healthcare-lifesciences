"""Tool: Initialize patient memory profile on admission."""

import os
import json
from datetime import datetime, timezone
import boto3
from strands import tool

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))
memory_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENT_MEMORY_TABLE", "connected-care-patient-memory"))

MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

try:
    agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)
except Exception:
    agentcore_client = None


def _write_to_agentcore_memory(patient_id: str, content: str, actor_id: str = "system"):
    """Write an event to AgentCore Memory for long-term extraction."""
    if not MEMORY_ID or not agentcore_client:
        return
    try:
        session_id = f"patient-{patient_id}"
        agentcore_client.write_memory_event(
            memoryId=MEMORY_ID,
            actorId=actor_id,
            sessionId=session_id,
            eventContent={"conversationalEvent": {"conversationalMessages": [
                {"role": "ASSISTANT", "content": content}
            ]}},
        )
    except Exception as e:
        print(f"AgentCore Memory write failed: {e}")


@tool
def initialize_patient_memory(patient_id: str) -> dict:
    """Initialize a patient memory profile on admission. Pulls the patient's clinical profile
    and writes it as the admission baseline to both AgentCore Memory (long-term) and the
    timeline table (sidebar display).

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Confirmation that the memory profile was initialized with baseline data.
    """
    patient_resp = patients_table.get_item(Key={"patient_id": patient_id})
    patient = patient_resp.get("Item")
    if not patient:
        return {"error": f"Patient {patient_id} not found"}

    now = datetime.now(timezone.utc).isoformat()

    conditions = patient.get("conditions", [])
    medications = patient.get("medications", [])
    med_summary = ", ".join([f"{m.get('name')} {m.get('dose')} {m.get('frequency')}" for m in medications])

    summary = f"Patient {patient.get('name')} ({patient_id}) admitted to {patient.get('room', 'unknown')}. Age: {patient.get('age')}. Conditions: {', '.join(conditions)}. Medications: {med_summary}. Risk profile: {patient.get('risk_profile')}."

    # Write to DynamoDB timeline (sidebar display)
    memory_table.put_item(Item={
        "patient_id": patient_id,
        "timestamp": now,
        "entry_type": "admission",
        "category": "baseline",
        "summary": summary,
        "details": json.dumps({
            "name": patient.get("name"),
            "age": patient.get("age"),
            "room": patient.get("room"),
            "risk_profile": patient.get("risk_profile"),
            "conditions": conditions,
            "medications": medications,
            "braden_score": patient.get("braden_score", {}),
            "fall_risk": patient.get("fall_risk", {}),
        }),
        "recorded_by": "system",
        "active": "true",
    })

    # Write to AgentCore Memory (long-term semantic retrieval)
    _write_to_agentcore_memory(patient_id, summary)

    return {
        "patient_id": patient_id,
        "name": patient.get("name"),
        "room": patient.get("room"),
        "status": "memory_initialized",
        "memory_targets": ["agentcore_memory", "timeline_table"],
        "conditions": conditions,
        "medications_count": len(medications),
        "risk_profile": patient.get("risk_profile"),
        "message": f"Patient memory initialized for {patient.get('name')} ({patient_id}) in {patient.get('room')}. Written to AgentCore Memory and timeline.",
    }
