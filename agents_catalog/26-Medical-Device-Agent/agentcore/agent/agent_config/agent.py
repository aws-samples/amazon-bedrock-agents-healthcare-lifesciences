"""Medical Device Coordinator agent task logic."""

from strands import Agent
from strands.models import BedrockModel

from agent.agent_config.tools.device_status import get_device_status, list_all_devices
from agent.agent_config.tools.clinical_trials import search_clinical_trials
from agent.agent_config.tools.pubmed_search import search_pubmed

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are a Medical Device Coordinator AI assistant for a healthcare organization.
You specialize in:
- Medical device status monitoring and management
- Medical literature research using PubMed
- Clinical trials information lookup
- Providing evidence-based medical device recommendations

Always provide device IDs when referencing specific equipment and cite sources when providing medical information.
Format your responses clearly with relevant medical context."""

ALL_TOOLS = [
    get_device_status,
    list_all_devices,
    search_clinical_trials,
    search_pubmed,
]


async def agent_task(user_message: str, session_id: str):
    """Create and run the medical device coordinator agent."""
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID, max_tokens=4000, temperature=0.1),
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )

    stream = agent.stream_async(user_message)
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]
