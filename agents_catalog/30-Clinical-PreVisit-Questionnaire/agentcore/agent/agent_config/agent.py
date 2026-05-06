"""PVQ agent task logic."""

from strands.models import BedrockModel

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
FAST_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


async def agent_task(message: str, mode: str = "standard", session_id: str = "default"):
    """Run the PVQ agent."""
    if mode == "fast":
        from agent.agent_config.pvq_agent_fast import FastPVQAgent
        agent_instance = FastPVQAgent()
    else:
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent_instance = PVQStrandsAgent()

    response = agent_instance.chat(message)
    yield response
