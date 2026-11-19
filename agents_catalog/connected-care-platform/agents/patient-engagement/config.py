"""Patient Engagement Agent — Configuration"""

import os

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_ENGAGEMENT_PROFILES_TABLE = os.environ.get("DYNAMODB_ENGAGEMENT_PROFILES_TABLE", "connected-care-engagement-profiles")
DYNAMODB_MEDICATIONS_TABLE = os.environ.get("DYNAMODB_MEDICATIONS_TABLE", "connected-care-medications")
DYNAMODB_APPOINTMENTS_TABLE = os.environ.get("DYNAMODB_APPOINTMENTS_TABLE", "connected-care-appointments")
DYNAMODB_ADHERENCE_TABLE = os.environ.get("DYNAMODB_ADHERENCE_TABLE", "connected-care-medication-adherence")
DYNAMODB_COMMUNICATIONS_TABLE = os.environ.get("DYNAMODB_COMMUNICATIONS_TABLE", "connected-care-communications")
DYNAMODB_CARE_PLANS_TABLE = os.environ.get("DYNAMODB_CARE_PLANS_TABLE", "connected-care-care-plans")
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE", "connected-care-pe-connections")
EVENTBRIDGE_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")

AGENT_MODEL = os.environ.get("AGENT_MODEL", "us.anthropic.claude-opus-4-6-v1")
AGENT_NAME = "Patient Engagement Agent"

NOTIFICATION_CHANNELS = ["sms", "email", "phone", "app"]

EVENT_TYPES = [
    "patient.notification_sent", "appointment.noshow_predicted",
    "patient.discharged", "medication.adherence_alert",
    "appointment.scheduled", "appointment.cancelled",
    "patient.onboarded", "caregiver.notified",
    "care_plan.created", "telehealth.requested",
    "communication.preference_updated",
]
