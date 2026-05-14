"""Tool: List all monitored patients with current status."""

import os
import boto3
from strands import tool
from .phi_access import get_actor_email

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))
care_team_table = dynamodb.Table(os.environ.get("DYNAMODB_CARE_TEAM_TABLE", "connected-care-care-team"))


@tool
def list_patients() -> dict:
    """List all monitored patients with their current status summary.
    Only shows full details for patients the user is on the care team for.

    Returns:
        A list of all patients including their ID, name, room, risk profile,
        and active conditions. PHI is redacted for patients the user is not authorized to view.
    """
    response = patients_table.scan()
    items = response.get("Items", [])
    email = get_actor_email()

    # Get all care team assignments for this user
    authorized_patients = set()
    if email:
        try:
            ct_resp = care_team_table.scan()
            for ct in ct_resp.get("Items", []):
                if email in ct.get("team_members", []):
                    authorized_patients.add(ct["patient_id"])
        except Exception:
            pass

    patients = []
    for item in items:
        pid = item["patient_id"]
        if not email or pid in authorized_patients:
            patients.append({
                "patient_id": pid,
                "name": item.get("name", "Unknown"),
                "age": int(item.get("age", 0)),
                "room": item.get("room", "Unknown"),
                "risk_profile": item.get("risk_profile", "unknown"),
                "conditions": item.get("conditions", []),
            })
        else:
            patients.append({
                "patient_id": pid,
                "name": "[REDACTED — not on care team]",
                "room": item.get("room", "Unknown"),
                "risk_profile": item.get("risk_profile", "unknown"),
                "conditions": ["[REDACTED]"],
                "phi_restricted": True,
            })

    risk_order = {"critical": 0, "moderate": 1, "stable": 2, "unknown": 3}
    patients.sort(key=lambda p: risk_order.get(p["risk_profile"], 3))

    return {
        "total_patients": len(patients),
        "patients": patients,
    }
