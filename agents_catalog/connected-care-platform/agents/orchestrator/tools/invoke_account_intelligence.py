"""Tool: Invoke the Account Intelligence Agent."""

import os
from strands import tool
from .invoke_agent import invoke_agent

AI_TARGET = os.environ.get("AI_RUNTIME_ARN") or os.environ.get("AI_FUNCTION_NAME", "connected-care-account-intelligence-agent-api")


@tool
def invoke_account_intelligence(prompt: str) -> dict:
    """Send a prompt to the Account Intelligence Agent.

    Args:
        prompt: Natural language prompt for the Account Intelligence Agent

    Returns:
        The agent's response with timing information.
    """
    return invoke_agent(AI_TARGET, "Account Intelligence", prompt)
