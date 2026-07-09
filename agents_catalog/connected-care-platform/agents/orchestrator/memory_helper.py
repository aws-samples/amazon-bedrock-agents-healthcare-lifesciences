"""Shared AgentCore Memory helper for all Connected Care agents.

Creates a session manager and tracks memory usage for UI indicators.
"""

import os
import logging
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")
logger = logging.getLogger(__name__)


def create_session_manager(session_id: str, actor_id: str = "system"):
    """Create an AgentCore Memory session manager."""
    if not MEMORY_ID:
        return None

    config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
    )

    return AgentCoreMemorySessionManager(
        agentcore_memory_config=config,
        region_name=REGION,
    )


def get_memory_context(session_manager) -> dict:
    """Check what memory was used and return context for the UI.

    Returns a dict with:
      - used: bool (was memory active)
      - short_term: int (number of prior messages in session)
      - long_term: list of str (types of long-term memory retrieved)
    """
    if not session_manager:
        return {"used": False, "short_term": 0, "long_term": []}

    context = {"used": True, "short_term": 0, "long_term": []}

    try:
        # Check short-term: how many messages were loaded from session history
        session = getattr(session_manager, "_session", None)
        if session:
            messages = getattr(session, "messages", [])
            # Count prior messages (excluding the current user message)
            prior = len([m for m in messages if isinstance(m, dict)]) - 1
            context["short_term"] = max(0, prior)
    except Exception as e:
        logger.debug(f"Memory context check failed: {e}")

    return context
