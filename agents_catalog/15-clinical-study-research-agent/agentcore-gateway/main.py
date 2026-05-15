"""Clinical Study Research Agent — AgentCore Gateway + Multiple MCP Servers.

This example demonstrates connecting an agent to multiple external MCP servers
via AgentCore Gateway: ClinicalTrials.gov, PubMed, and OpenFDA.

The agent discovers all available tools at runtime from the gateway — no local
tool implementations needed. Adding a new data source is a gateway-target
addition, not a code change.

Setup:
    agentcore add gateway --name ClinicalResearchGateway

    # ClinicalTrials.gov MCP server
    agentcore add gateway-target \
        --type mcp-server \
        --name ClinicalTrials \
        --endpoint https://mcp.clinicaltrials.example.com/mcp \
        --gateway ClinicalResearchGateway

    # PubMed MCP server
    agentcore add gateway-target \
        --type mcp-server \
        --name PubMed \
        --endpoint https://mcp.pubmed.example.com/mcp \
        --gateway ClinicalResearchGateway

    # OpenFDA MCP server (drug approvals)
    agentcore add gateway-target \
        --type mcp-server \
        --name OpenFDA \
        --endpoint https://mcp.openfda.example.com/mcp \
        --gateway ClinicalResearchGateway

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

GATEWAY_URL = os.getenv("AGENTCORE_GATEWAY_CLINICALRESEARCHGATEWAY_URL")

SYSTEM_PROMPT = """You are a clinical study research assistant with access to multiple biomedical databases.

Available data sources (discovered automatically via gateway):
- ClinicalTrials.gov — search and retrieve clinical trial information
- PubMed — search biomedical literature
- OpenFDA — query FDA drug approval and labeling data

Workflow:
1. Understand the research question
2. Query the appropriate data source(s)
3. Synthesize findings across sources when relevant
4. Cite sources with identifiers (NCT IDs, PMIDs, drug names)

Guidelines:
- Use specific search terms for better results
- Cross-reference findings across databases when possible
- Clearly distinguish between trial data, literature evidence, and regulatory data
- If a query returns no results, suggest alternative search terms
"""


async def get_gateway_tools():
    """Discover all tools from the AgentCore Gateway.

    The gateway aggregates tools from all connected MCP servers
    (ClinicalTrials, PubMed, OpenFDA). The agent sees a unified
    tool catalog without knowing which backend serves each tool.
    """
    if not GATEWAY_URL:
        return []
    async with streamablehttp_client(GATEWAY_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            logger.info(f"Discovered {len(tools)} tools from gateway")
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
        logger.warning("No gateway tools available — agent will use reasoning only")

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
