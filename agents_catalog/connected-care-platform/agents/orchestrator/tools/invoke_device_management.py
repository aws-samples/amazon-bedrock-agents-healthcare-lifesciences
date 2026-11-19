"""Tool: Invoke the Device Management Agent."""

import os
from strands import tool
from .invoke_agent import invoke_agent

DM_TARGET = os.environ.get("DM_RUNTIME_ARN") or os.environ.get("DM_FUNCTION_NAME", "connected-care-device-agent-api")


@tool
def invoke_device_management(prompt: str) -> dict:
    """Send a prompt to the Device Management Agent.

    Args:
        prompt: Natural language prompt for the Device Management Agent

    Returns:
        The agent's response with timing information.
    """
    return invoke_agent(DM_TARGET, "Device Management", prompt)
