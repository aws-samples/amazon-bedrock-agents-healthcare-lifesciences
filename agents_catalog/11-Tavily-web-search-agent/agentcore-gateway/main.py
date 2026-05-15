"""Tavily Web Search Agent — AgentCore Gateway + External MCP Server pattern.

This example demonstrates connecting an agent to an external MCP server (Tavily)
via AgentCore Gateway, rather than embedding API calls as local @tool functions.

Benefits:
- Agent code has zero API keys or HTTP calls
- Tools are discoverable via MCP protocol
- Cedar policies can restrict tool access
- Adding/removing tools requires no code changes

Setup:
    agentcore add gateway --name TavilyGateway
    agentcore add gateway-target \
        --type mcp-server \
        --name TavilySearch \
        --endpoint https://mcp.tavily.com/mcp \
        --gateway TavilyGateway \
        --outbound-auth oauth \
        --oauth-client-id $TAVILY_CLIENT_ID \
        --oauth-client-secret $TAVILY_CLIENT_SECRET \
        --oauth-discovery-url https://auth.tavily.com/.well-known/openid-configuration
    agentcore deploy -y
"""

import asyncio
import os
import logging

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

logger = logging.getLogger(__name__)

GATEWAY_URL = os.getenv("AGENTCORE_GATEWAY_TAVILYGATEWAY_URL")

SYSTEM_PROMPT = """You are a research assistant specializing in web-based information retrieval.

1. Analyze queries precisely
2. Search for authoritative, current sources
3. Deliver concise, factual responses with source citations

Citation format: "[Factual response] (source: [URL])"
"""


async def get_gateway_tools():
    """Discover tools from the AgentCore Gateway MCP endpoint."""
    if not GATEWAY_URL:
        return []
    async with streamablehttp_client(GATEWAY_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return tools


app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        streaming=True,
    )

    tools = asyncio.run(get_gateway_tools())

    if not tools:
        logger.warning("No gateway tools available — running without external tools")

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools if tools else [],
    )

    prompt = payload.get("prompt", "")
    response = agent(prompt)
    return {"response": str(response)}


if __name__ == "__main__":
    app.run()
