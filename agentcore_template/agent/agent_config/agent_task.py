from .context import TemplateContext
from .memory_hook_provider import MemoryHook
from .utils import get_ssm_parameter
from agent.agent_config.agent import TemplateAgent
from bedrock_agentcore.memory import MemoryClient
from agent.agent_config.tools.sample_tools import get_system_info
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

memory_client = MemoryClient()


async def agent_task(user_message: str, session_id: str, actor_id: str):
    agent = TemplateContext.get_agent_ctx()

    response_queue = TemplateContext.get_response_queue_ctx()
    gateway_access_token = TemplateContext.get_gateway_token_ctx()

    if not gateway_access_token:
        raise RuntimeError("Gateway Access token is none")
    try:
        if agent is None:
            # Create memory hook (using a default memory_id for now)
            memory_hook = MemoryHook(
                memory_client=memory_client,
                memory_id=get_ssm_parameter("/app/myapp/agentcore/memory_id"),
                actor_id=actor_id,
                session_id=session_id,
            )

            agent = TemplateAgent(
                bearer_token=gateway_access_token,
                memory_hook=memory_hook,
                tools=[get_system_info],  # Add custom tools here as needed
            )

            TemplateContext.set_agent_ctx(agent)

        async for chunk in agent.stream(user_query=user_message):
            await response_queue.put(chunk)

    except Exception as e:
        logger.exception("Agent execution failed.")
        await response_queue.put(f"Error: {str(e)}")
    finally:
        await response_queue.finish()
