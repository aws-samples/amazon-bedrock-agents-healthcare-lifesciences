"""BedrockAgentCoreApp entrypoint for the Clinical Trial Protocol Assistant."""

from agent.agent_config.agent import create_agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()
agent = create_agent()


@app.entrypoint
async def invoke(payload):
    """Invoke the clinical trial protocol assistant agent with streaming."""
    user_input = payload.get("prompt")

    tool_name = None
    async for event in agent.stream_async(user_input):
        if (
            "current_tool_use" in event
            and event["current_tool_use"].get("name") != tool_name
        ):
            tool_name = event["current_tool_use"]["name"]
            yield f"\n\n🔧 Using tool: {tool_name}\n\n"

        if "data" in event:
            yield event["data"]


if __name__ == "__main__":
    app.run()
