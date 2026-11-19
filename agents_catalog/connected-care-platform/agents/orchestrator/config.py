"""Orchestrator Agent — Configuration"""

import os

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE", "connected-care-orch-connections")
EVENTBRIDGE_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")

AGENT_MODEL = os.environ.get("AGENT_MODEL", "us.anthropic.claude-opus-4-6-v1")
AGENT_NAME = "Orchestrator Agent"

# Domain agent WebSocket URLs
PM_WS_URL = os.environ.get("PM_WS_URL", "")
DM_WS_URL = os.environ.get("DM_WS_URL", "")
PE_WS_URL = os.environ.get("PE_WS_URL", "")

AGENT_LABELS = {
    "patient-monitoring": "Patient Monitoring",
    "device-management": "Device Management",
    "patient-engagement": "Patient Engagement",
}
