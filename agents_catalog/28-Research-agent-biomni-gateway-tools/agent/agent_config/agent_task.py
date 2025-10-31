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


async def agent_task(user_message: str, session_id: str, actor_id: str, bedrock_model_id: str = None):
    agent = ResearchContext.get_agent_ctx()

    response_queue = ResearchContext.get_response_queue_ctx()
    gateway_access_token = ResearchContext.get_gateway_token_ctx()

    if not gateway_access_token:
        raise RuntimeError("Gateway Access token is none")
    
    # Check if model has changed - update config instead of recreating agent
    if agent is not None and bedrock_model_id is not None:
        if agent.model_id != bedrock_model_id:
            logger.info(f"Model changed from {agent.model_id} to {bedrock_model_id}, updating agent configuration")
            # Update the model configuration dynamically using the new method
            success = agent.update_model(bedrock_model_id)
            if success:
                logger.info(f"Agent model configuration updated successfully to: {bedrock_model_id}")
            else:
                logger.error(f"Failed to update model configuration, will recreate agent")
                agent = None
                ResearchContext.set_agent_ctx(None)
    # Below option uses a self managed memory hook with the agent 
    """ try:
        if agent is None:
            # Create memory hook (using a default memory_id for now)
            memory_hook = MemoryHook(
                memory_client=memory_client,
                memory_id=get_ssm_parameter("/app/researchapp/agentcore/memory_id"),
                actor_id=actor_id,
                session_id=session_id,
            )
            logger.info("Memory hook created successfully")
            agent = ResearchAgent(
                bearer_token=gateway_access_token,
                memory_hook=memory_hook,
                tools=[]
                #tools=[query_pubmed],  # Add custom tools here as needed
            )

            logger.info("Agent created successfully")   

            ResearchContext.set_agent_ctx(agent)

        async for chunk in agent.stream(user_query=user_message):
            await response_queue.put(chunk)
 """
    # Below option uses fully managed Memory Sessions Manager from Strands
    try:
        if agent is None:
            MEM_ID = get_ssm_parameter("/app/researchapp/agentcore/memory_id")
            ACTOR_ID = actor_id
            SESSION_ID = session_id


            # Configure memory
            agentcore_memory_config = AgentCoreMemoryConfig(
                memory_id=MEM_ID,
                session_id=SESSION_ID,
                actor_id=ACTOR_ID
            )

            # Create session manager
            session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=agentcore_memory_config
            )

            # Create agent with optional model_id
            agent_kwargs = {
                "bearer_token": gateway_access_token,
                "session_manager": session_manager,
                "tools": []
                #tools=[query_pubmed],  # Add custom tools here as needed
            }
            
            # Add model_id if provided
            if bedrock_model_id:
                agent_kwargs["bedrock_model_id"] = bedrock_model_id
                logger.info(f"Using model: {bedrock_model_id}")
            
            agent = ResearchAgent(**agent_kwargs)

            logger.info("Agent created successfully")   

            ResearchContext.set_agent_ctx(agent)

        async for chunk in agent.stream(user_query=user_message):
            await response_queue.put(chunk)

    except Exception as e:
        logger.exception("Agent execution failed.")
        await response_queue.put(f"Error: {str(e)}")
    finally:
        await response_queue.finish()
