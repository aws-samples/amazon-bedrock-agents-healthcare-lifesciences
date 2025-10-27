from .context import ResearchContext
from .memory_hook_provider import MemoryHook
from .utils import get_ssm_parameter
from agent.agent_config.agent import ResearchAgent
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from agent.agent_config.tools.research_tools import query_pubmed
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

memory_client = MemoryClient()


async def agent_task(user_message: str, session_id: str, actor_id: str, use_semantic_search: bool=False):
    agent = ResearchContext.get_agent_ctx()
    response_queue = ResearchContext.get_response_queue_ctx()
    gateway_access_token = ResearchContext.get_gateway_token_ctx()

    if not gateway_access_token:
        raise RuntimeError("Gateway Access token is none")

    try:
        if agent is None:
            MEM_ARN = get_ssm_parameter("/app/researchapp/agentcore/memory_id")
            MEM_ID = MEM_ARN.split("/")[-1]

            # Configure memory
            agentcore_memory_config = AgentCoreMemoryConfig(
                memory_id=MEM_ID,
                session_id=session_id,
                actor_id=actor_id
            )

            # Create session manager
            session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=agentcore_memory_config
            )

            # Create agent with semantic search enabled
            agent = ResearchAgent(
                bearer_token=gateway_access_token,
                session_manager=session_manager,
            )
  
            ResearchContext.set_agent_ctx(agent)

        # Get relevant tools based on the user query
        if use_semantic_search:
            relevant_tools = agent._get_relevant_tools(user_message)
            agent.agent.tools = relevant_tools
            logger.info(f"Using Semantic Search: Updated agent with {len(relevant_tools)} relevant tools")
        else:
            agent.agent.tools = agent.gateway_client.list_tools_sync()
            logger.info(f"Retrieved all tools. (Semantic not enabled)")

        # Stream response with query-specific tools
        async for chunk in agent.stream(user_query=user_message):
            await response_queue.put(chunk)

    except Exception as e:
        logger.exception("Agent execution failed.")
        await response_queue.put(f"Error: {str(e)}")
    finally:
        await response_queue.finish()
