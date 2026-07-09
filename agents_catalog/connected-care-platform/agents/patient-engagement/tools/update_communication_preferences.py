"""Tool: Update communication preferences for a patient."""

import os
from datetime import datetime, timezone

import boto3
from strands import tool
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
profiles_table = dynamodb.Table(os.environ.get("DYNAMODB_ENGAGEMENT_PROFILES_TABLE", "connected-care-engagement-profiles"))


@tool
def update_communication_preferences(
    patient_id: str,
    preferred_channel: str = "",
    language: str = "",
    contact_times: str = "",
) -> dict:
    """Update communication preferences for a patient.

    Updates one or more communication preference fields in the patient's
    engagement profile.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        preferred_channel: Preferred communication channel (e.g., "phone", "sms", "email", "app")
        language: Preferred language (e.g., "English", "Spanish")
        contact_times: Preferred contact times (e.g., "9am-5pm", "anytime")

    Returns:
        Confirmation of the updated preferences.
    """
    # Verify profile exists
    profile_resp = profiles_table.get_item(Key={"patient_id": patient_id})
    profile = profile_resp.get("Item")
    if not profile:
        return {"error": f"No engagement profile found for patient {patient_id}"}

    update_parts = []
    attr_names = {}
    attr_values = {}

    if preferred_channel:
        update_parts.append("communication_preferences.preferred_channel = :channel")
        attr_values[":channel"] = preferred_channel

    if language:
        update_parts.append("communication_preferences.#lang = :language")
        attr_names["#lang"] = "language"
        attr_values[":language"] = language

    if contact_times:
        update_parts.append("communication_preferences.contact_times = :times")
        attr_values[":times"] = contact_times

    if not update_parts:
        return {"error": "No preferences provided to update. Specify at least one of: preferred_channel, language, contact_times"}

    now = datetime.now(timezone.utc).isoformat()
    update_parts.append("updated_at = :now")
    attr_values[":now"] = now

    update_expression = "SET " + ", ".join(update_parts)

    update_kwargs = {
        "Key": {"patient_id": patient_id},
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": attr_values,
    }
    if attr_names:
        update_kwargs["ExpressionAttributeNames"] = attr_names

    profiles_table.update_item(**update_kwargs)

    updated_fields = {}
    if preferred_channel:
        updated_fields["preferred_channel"] = preferred_channel
    if language:
        updated_fields["language"] = language
    if contact_times:
        updated_fields["contact_times"] = contact_times

    return sanitize({
        "patient_id": patient_id,
        "updated_fields": updated_fields,
        "updated_at": now,
        "message": f"Communication preferences updated for patient {patient_id}",
    })
