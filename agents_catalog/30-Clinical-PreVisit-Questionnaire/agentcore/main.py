"""Clinical PreVisit Questionnaire Agent — AgentCore runtime."""

from agent.agent_config.agent import agent_task
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import logging

logging.basicConfig(level=logging.INFO)
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload, context):
    message = payload.get("message") or payload.get("prompt", "")
    mode = payload.get("mode", "standard")
    session_id = getattr(context, "session_id", "default")

    async for chunk in agent_task(message=message, mode=mode, session_id=session_id):
        yield chunk


if __name__ == "__main__":
    app.run()
