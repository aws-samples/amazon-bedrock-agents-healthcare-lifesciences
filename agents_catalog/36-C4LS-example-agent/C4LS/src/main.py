import os
from strands import Agent, tool, AgentSkills, Skill
from strands_tools import file_read, shell
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model
import pathlib

app = BedrockAgentCoreApp()
log = app.logger

REGION = os.getenv("AWS_REGION")

# Define MCP connections to Claude connectors
pubmed_mcp_client = get_streamable_http_mcp_client("https://pubmed.mcp.claude.com/mcp")
opentargets_mcp_client = get_streamable_http_mcp_client(
    "https://mcp.platform.opentargets.org/mcp"
)

# Load agent skills defined in skills folder
plugin = AgentSkills(skills=f"{pathlib.Path(__file__).resolve().parent}/skills/")


@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(context, "session_id", "default")
    user_id = payload.get("user_id") or "default-user"

    # Create code interpreter
    code_interpreter = AgentCoreCodeInterpreter(
        region=REGION, session_name=session_id, auto_create=True, persist_sessions=True
    )

    # Create agent
    agent = Agent(
        model=load_model(),
        plugins=[plugin],
        system_prompt="""
            You are a helpful assistant with code execution capabilities. Use tools when appropriate.
        """,
        tools=[
            code_interpreter.code_interpreter,
            pubmed_mcp_client,
            opentargets_mcp_client,
            file_read,
            shell,
        ],
    )

    # Execute and format response
    stream = agent.stream_async(payload.get("prompt"))

    async for event in stream:
        # Handle Text parts of the response
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
