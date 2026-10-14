"""Tool: Invoke the Inventory Management Agent."""

import os
from strands import tool
from .invoke_agent import invoke_agent

IM_TARGET = os.environ.get("IM_RUNTIME_ARN") or os.environ.get("IM_FUNCTION_NAME", "connected-care-inventory-agent-api")


@tool
def invoke_inventory_management(prompt: str) -> dict:
    """Send a prompt to the Inventory Management Agent.

    Args:
        prompt: Natural language prompt for the Inventory Management Agent

    Returns:
        The agent's response with timing information.
    """
    return invoke_agent(IM_TARGET, "Inventory Management", prompt)
