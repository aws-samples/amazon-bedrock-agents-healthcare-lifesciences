"""Tool: Create a care plan for a patient."""

import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
care_plans_table = dynamodb.Table(os.environ.get("DYNAMODB_CARE_PLANS_TABLE", "connected-care-care-plans"))


@tool
def create_care_plan(
    patient_id: str,
    plan_type: str,
    conditions_to_monitor: list,
    follow_up_schedule: list,
    notes: str = "",
) -> dict:
    """Create a new care plan for a patient.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        plan_type: Type of care plan (e.g., "post-discharge", "chronic-management", "preventive")
        conditions_to_monitor: List of conditions to monitor (e.g., ["CHF exacerbation", "Blood glucose"])
        follow_up_schedule: List of follow-up items (e.g., [{"type": "Cardiology", "days": 7}])
        notes: Additional notes for the care plan

    Returns:
        Confirmation of the created care plan with generated plan ID.
    """
    plan_id = f"CP-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    care_plans_table.put_item(Item={
        "patient_id": patient_id,
        "plan_id": plan_id,
        "plan_type": plan_type,
        "conditions_to_monitor": conditions_to_monitor,
        "follow_up_schedule": follow_up_schedule,
        "notes": notes,
        "status": "active",
        "created_at": now,
    })

    return sanitize({
        "plan_id": plan_id,
        "patient_id": patient_id,
        "plan_type": plan_type,
        "conditions_to_monitor": conditions_to_monitor,
        "follow_up_schedule": follow_up_schedule,
        "notes": notes,
        "status": "active",
        "created_at": now,
        "message": f"Care plan {plan_id} created for patient {patient_id}",
    })
