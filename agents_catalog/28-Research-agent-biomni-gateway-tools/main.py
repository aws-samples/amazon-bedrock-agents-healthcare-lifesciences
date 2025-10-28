from agent.agent_config.agent import agent_task
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import logging
import os

# Environment flags
os.environ["STRANDS_OTEL_ENABLE_CONSOLE_EXPORT"] = "true"
os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bedrock app
app = BedrockAgentCoreApp()

USE_SEMANTIC_SEARCH = True

@app.entrypoint
async def invoke(payload, context):
    user_message = payload["prompt"]
    actor_id = payload.get("actor_id", "DEFAULT")
    session_id = context.session_id

    if not session_id:
        raise Exception("Context session_id is not set")

    # Stream response directly from agent_task
    async for chunk in agent_task(
        user_message=user_message,
        session_id=session_id,
        actor_id=actor_id,
        use_semantic_search=USE_SEMANTIC_SEARCH,
    ):
        yield chunk

if __name__ == "__main__":
    print('running')
    app.run()