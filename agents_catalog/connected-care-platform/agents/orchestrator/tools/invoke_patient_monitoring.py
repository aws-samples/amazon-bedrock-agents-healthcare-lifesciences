"""Tool: Invoke the Patient Monitoring Agent."""

import os
from strands import tool
from .invoke_agent import invoke_agent

# Supports both Lambda (PM_FUNCTION_NAME) and AgentCore (PM_RUNTIME_ARN) modes
PM_TARGET = os.environ.get("PM_RUNTIME_ARN") or os.environ.get("PM_FUNCTION_NAME", "connected-care-agent-api")


@tool
def invoke_patient_monitoring(prompt: str) -> dict:
    """Send a prompt to the Patient Monitoring Agent.

    Args:
        prompt: Natural language prompt for the Patient Monitoring Agent

    Returns:
        The agent's response with timing information.
    """
    return invoke_agent(PM_TARGET, "Patient Monitoring", prompt)
