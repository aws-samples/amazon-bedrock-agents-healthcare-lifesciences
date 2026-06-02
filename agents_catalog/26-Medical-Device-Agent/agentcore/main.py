"""Medical Device Coordinator Agent — AgentCore runtime."""

from agent.agent_config.agent import agent_task
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import logging

logging.basicConfig(level=logging.INFO)
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload, context):
    user_message = payload.get("prompt", "")
    session_id = getattr(context, "session_id", "default")

    async for chunk in agent_task(user_message=user_message, session_id=session_id):
        yield chunk


if __name__ == "__main__":
    app.run()
