"""Clinical Prior Authorization Agent — AgentCore runtime."""

from agent.agent_config.agent import agent_task
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import logging
import os

os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload, context):
    user_message = payload.get("prompt") or payload.get("patient_data", "")
    session_id = getattr(context, "session_id", "default")

    async for chunk in agent_task(
        user_message=user_message,
        session_id=session_id,
    ):
        yield chunk


if __name__ == "__main__":
    print("running")
    app.run()
