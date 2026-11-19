"""Tool: Invoke the Patient Engagement Agent."""

import os
from strands import tool
from .invoke_agent import invoke_agent

PE_TARGET = os.environ.get("PE_RUNTIME_ARN") or os.environ.get("PE_FUNCTION_NAME", "connected-care-engagement-agent-api")


@tool
def invoke_patient_engagement(prompt: str) -> dict:
    """Send a prompt to the Patient Engagement Agent.

    Args:
        prompt: Natural language prompt for the Patient Engagement Agent

    Returns:
        The agent's response with timing information.
    """
    return invoke_agent(PE_TARGET, "Patient Engagement", prompt)
