"""Tool: Get discharge plan for a patient."""

import os
import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
profiles_table = dynamodb.Table(os.environ.get("DYNAMODB_ENGAGEMENT_PROFILES_TABLE", "connected-care-engagement-profiles"))


@tool
def get_discharge_plan(patient_id: str) -> dict:
    """Retrieve the discharge plan for a patient.

    Includes discharge date, conditions to monitor, follow-up appointments,
    and activity restrictions.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        Discharge plan details or indication that no plan exists.
    """
    response = profiles_table.get_item(Key={"patient_id": patient_id})
    profile = response.get("Item")
    if not profile:
        return {"error": f"No engagement profile found for patient {patient_id}"}

    discharge_plan = profile.get("discharge_plan")
    if not discharge_plan:
        return {
            "patient_id": patient_id,
            "message": f"No discharge plan found for patient {patient_id}. Patient may still be admitted or plan not yet created.",
        }

    return sanitize({
        "patient_id": patient_id,
        "discharge_date": discharge_plan.get("discharge_date"),
        "conditions_to_monitor": discharge_plan.get("conditions_to_monitor", []),
        "follow_up_appointments": discharge_plan.get("follow_up_appointments", []),
        "activity_restrictions": discharge_plan.get("activity_restrictions"),
    })
