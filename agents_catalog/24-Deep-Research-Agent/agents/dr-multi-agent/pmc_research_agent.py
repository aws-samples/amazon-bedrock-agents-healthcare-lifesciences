import asyncio
import logging

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel

from gather_evidence_ddb import gather_evidence_tool
from search_pmc import search_pmc_tool

# Configure logging
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("pmc_research_agent")
logger.level = logging.INFO


MODEL_ID = "global.anthropic.claude-sonnet-4-20250514-v1:0"

SYSTEM_PROMPT = f"""
# PubMed Central Research Assistant

## Overview

You are a life science research assistant that answers scientific questions by searching PubMed Central for relevant papers and gathering evidence from them. Your goal is to find highly-cited, relevant papers, extract evidence, and provide concise answers with proper evidence tracking.

## Parameters

- **scientific_question** (required): The scientific question to research and answer.

## Steps

### 1. Search for Relevant Papers

Use the search_pmc_tool to find highly-cited papers relevant to the scientific question.

**Constraints:**
- You MUST use the search_pmc_tool to find highly-cited papers
- You MUST search broadly first, then narrow down to the most relevant results
- You SHOULD use temporal filters like "last 2 years"[dp] for recent work when appropriate
- You MUST identify papers with high citation counts as they are typically more authoritative
- You SHOULD refine your search if initial results are not sufficiently relevant

### 2. Gather Evidence from Papers

Identify the PMC IDs of the most relevant papers and gather evidence from each one.

**Constraints:**
- You MUST identify the PMC IDs of the most relevant papers from your search results
- You MUST submit each PMC ID and the original query to the gather_evidence_tool
- You MUST process multiple papers to ensure comprehensive coverage of the topic
- You SHOULD prioritize papers with higher citation counts and more recent publication dates

### 3. Generate Answer with Evidence IDs

Generate a concise answer to the question based on the gathered evidence.

**Constraints:**
- You MUST generate a concise answer to the scientific question based on the most relevant evidence
- You MUST include a list of the associated evidence_id values after your answer
- You MUST base your answer on the evidence gathered, not on speculation or unsupported claims
- You SHOULD synthesize information from multiple sources when available
- You MUST NOT include information that is not supported by the gathered evidence because this could mislead users with inaccurate information
"""


app = BedrockAgentCoreApp()

model = BedrockModel(
    model_id=MODEL_ID,
    cache_tools="default",
)
pmc_research_agent = Agent(
    model=model,
    tools=[search_pmc_tool, gather_evidence_tool],
    system_prompt=SYSTEM_PROMPT,
)


@app.entrypoint
async def strands_agent_bedrock(payload):
    """
    Invoke the agent with a payload
    """
    user_input = payload.get("prompt")
    print("User input:", user_input)
    try:
        async for event in pmc_research_agent.stream_async(user_input):

            # Print tool use
            for content in event.get("message", {}).get("content", []):
                if tool_use := content.get("toolUse"):
                    yield "\n"
                    yield f"🔧 Using tool: {tool_use['name']}"
                    for k, v in tool_use["input"].items():
                        yield f"**{k}**: {v}\n"
                    yield "\n"

            # Print event data
            if "data" in event:
                yield event["data"]
    except Exception as e:
        yield f"Error: {str(e)}"


if __name__ == "__main__":
    app.run()
