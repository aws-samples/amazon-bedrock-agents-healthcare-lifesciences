"""Tool: Assess patient discharge readiness using memory timeline."""

import os
import json
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .phi_access import check_phi_access, phi_access_denied_response

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
memory_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENT_MEMORY_TABLE", "connected-care-patient-memory"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))
vitals_table = dynamodb.Table(os.environ.get("DYNAMODB_VITALS_TABLE", "connected-care-vitals"))


@tool
def assess_discharge_readiness(patient_id: str) -> dict:
    """Assess whether a patient is ready for discharge by reviewing their memory timeline,
    current vitals stability, medication tolerance, and unresolved clinical concerns.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Discharge readiness assessment with criteria checklist and recommendation.
    """
    # Get patient profile
    if not check_phi_access(patient_id):
        return phi_access_denied_response(patient_id)

    patient_resp = patients_table.get_item(Key={"patient_id": patient_id})
    patient = patient_resp.get("Item", {})

    # Get memory timeline
    mem_resp = memory_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
        ScanIndexForward=True,
    )
    entries = mem_resp.get("Items", [])

    # Get latest vitals
    vitals_resp = vitals_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
        ScanIndexForward=False,
        Limit=5,
    )
    recent_vitals = vitals_resp.get("Items", [])

    # Analyze memory for discharge-relevant signals
    med_responses = [e for e in entries if e.get("category") == "medication_response"]
    clinical_notes = [e for e in entries if e.get("category") == "clinical_note"]
    discharge_notes = [e for e in entries if e.get("category") == "discharge_planning"]
    care_plan_updates = [e for e in entries if e.get("category") == "care_plan"]

    # Build criteria checklist
    criteria = {
        "memory_initialized": len(entries) > 0,
        "total_observations": len(entries),
        "medication_responses_recorded": len(med_responses),
        "clinical_notes_recorded": len(clinical_notes),
        "discharge_planning_started": len(discharge_notes) > 0,
        "care_plan_updates": len(care_plan_updates),
        "vitals_available": len(recent_vitals) > 0,
    }

    # Compile recent observations for the agent to reason about
    recent_observations = []
    for e in entries[-10:]:
        recent_observations.append({
            "timestamp": e.get("timestamp"),
            "category": e.get("category"),
            "summary": e.get("summary"),
        })

    return {
        "patient_id": patient_id,
        "name": patient.get("name", "Unknown"),
        "room": patient.get("room", "Unknown"),
        "risk_profile": patient.get("risk_profile", "unknown"),
        "conditions": patient.get("conditions", []),
        "criteria": criteria,
        "recent_observations": recent_observations,
        "message": "Review the criteria and recent observations to assess discharge readiness. Consider vitals stability, medication tolerance, unresolved concerns, and care plan completion.",
    }
