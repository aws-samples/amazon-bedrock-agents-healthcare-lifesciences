"""Tool: Get patient engagement profile including communication preferences, care team, and caregivers."""

import os
import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
profiles_table = dynamodb.Table(os.environ.get("DYNAMODB_ENGAGEMENT_PROFILES_TABLE", "connected-care-engagement-profiles"))


@tool
def get_patient_engagement_profile(patient_id: str) -> dict:
    """Retrieve the full engagement profile for a patient.

    Includes communication preferences, care team members, family caregivers,
    discharge plan, health education history, and telehealth history.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Complete engagement profile for the patient.
    """
    response = profiles_table.get_item(Key={"patient_id": patient_id})
    profile = response.get("Item")
    if not profile:
        return {"error": f"No engagement profile found for patient {patient_id}"}

    return sanitize({
        "patient_id": patient_id,
        "name": profile.get("name"),
        "communication_preferences": profile.get("communication_preferences", {}),
        "care_team": profile.get("care_team", []),
        "family_caregivers": profile.get("family_caregivers", []),
        "discharge_plan": profile.get("discharge_plan"),
        "health_education": profile.get("health_education", []),
        "telehealth_history": profile.get("telehealth_history", []),
    })
