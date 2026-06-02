"""BedrockAgentCoreApp entrypoint for the USPTO Patent Search Agent."""

import logging
import os

from agent.agent_config.agent import create_agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

os.environ["STRANDS_OTEL_ENABLE_CONSOLE_EXPORT"] = "true"
os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload, context):
    user_message = payload["prompt"]
    agent = create_agent()

    async for event in agent.stream_async(user_message):
        if "data" in event:
            yield event["data"]


if __name__ == "__main__":
    app.run()
