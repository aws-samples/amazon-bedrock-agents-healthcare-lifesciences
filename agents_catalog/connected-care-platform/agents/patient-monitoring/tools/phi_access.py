"""PHI Access Control — checks if the requesting user is on the patient's care team."""

import os
import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
care_team_table = dynamodb.Table(os.environ.get("DYNAMODB_CARE_TEAM_TABLE", "connected-care-care-team"))

# Global variable set by the agent entrypoint with the current user's email
_current_actor_email = ""


def set_actor_email(email: str):
    global _current_actor_email
    _current_actor_email = email


def get_actor_email() -> str:
    return _current_actor_email


def check_phi_access(patient_id: str) -> bool:
    """Check if the current user is authorized to access PHI for this patient.

    Returns True if:
    - No actor email is set (system/orchestrator calls — always allowed)
    - The actor email is in the patient's care team
    """
    email = _current_actor_email
    if not email:
        return True  # System calls (no user context) are allowed

    try:
        resp = care_team_table.get_item(Key={"patient_id": patient_id})
        item = resp.get("Item")
        if not item:
            return False  # No care team assigned — access denied
        members = item.get("team_members", [])
        return email in members
    except Exception:
        return False  # Fail closed — deny access on error


def phi_access_denied_response(patient_id: str) -> dict:
    """Return a standardized access denied response."""
    return {
        "phi_access_denied": True,
        "patient_id": patient_id,
        "message": f"Access denied. You are not on the care team for patient {patient_id}. Use the 'Join Care Team' button to request access.",
    }
