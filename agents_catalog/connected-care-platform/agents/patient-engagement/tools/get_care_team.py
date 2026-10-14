"""Tool: Get care team members for a patient."""

import os
import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
profiles_table = dynamodb.Table(os.environ.get("DYNAMODB_ENGAGEMENT_PROFILES_TABLE", "connected-care-engagement-profiles"))


@tool
def get_care_team(patient_id: str) -> dict:
    """Retrieve the care team members assigned to a patient.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        List of care team members with role, name, and ID.
    """
    response = profiles_table.get_item(Key={"patient_id": patient_id})
    profile = response.get("Item")
    if not profile:
        return {"error": f"No engagement profile found for patient {patient_id}"}

    care_team = profile.get("care_team", [])
    return sanitize({
        "patient_id": patient_id,
        "care_team_size": len(care_team),
        "care_team": care_team,
    })
