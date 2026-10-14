"""Tool: Invoke the Field Service Intelligence Agent."""

import os
from strands import tool
from .invoke_agent import invoke_agent

FS_TARGET = os.environ.get("FS_RUNTIME_ARN") or os.environ.get("FS_FUNCTION_NAME", "connected-care-field-service-agent-api")


@tool
def invoke_field_service(prompt: str) -> dict:
    """Send a prompt to the Field Service Intelligence Agent.

    Args:
        prompt: Natural language prompt for the Field Service Agent

    Returns:
        The agent's response with timing information.
    """
    return invoke_agent(FS_TARGET, "Field Service", prompt)
