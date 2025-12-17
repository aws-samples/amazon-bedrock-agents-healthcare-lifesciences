import asyncio
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel
from strands.types.content import SystemContentBlock

from strands_tools import editor

from generate_report import generate_report_tool
from lead_config import MODEL_ID, SYSTEM_PROMPT
from pmc_research_agent import pmc_research_agent


@tool
def research_agent(prompt: str) -> str:
    """
    AI agent for researching scientific questions using articles from PubMed Central (PMC).

    You may delegate research tasks to this agent by providing clear text instructions in the prompt.

    Args:
        prompt: Scientific question to research using articles from PMC

    Returns:
        Concise answer to the question based on the most relevant evidence, followed by a list of the associated `evidence_id` values for citation analysis.
    """
    return pmc_research_agent(prompt)


app = BedrockAgentCoreApp()

# Define system content with cache points
system_content = [
    SystemContentBlock(text=SYSTEM_PROMPT),
    SystemContentBlock(cachePoint={"type": "default"}),
]

model = BedrockModel(
    model_id=MODEL_ID,
    max_tokens=10000,
    cache_tools="default",
    temperature=1,
    additional_request_fields={
        "anthropic_beta": ["interleaved-thinking-2025-05-14"],
        "reasoning_config": {
            "type": "enabled",
            "budget_tokens": 3000,
        },
    },
)

os.environ["BYPASS_TOOL_CONSENT"] = "true"

agent = Agent(
    model=model,
    tools=[research_agent, generate_report_tool, editor],
    system_prompt=system_content,
)


@app.entrypoint
async def strands_agent_bedrock(payload):
    """
    Invoke the agent with a payload
    """
    user_input = payload.get("prompt")
    print("User input:", user_input)
    try:
        async for event in agent.stream_async(user_input):

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
