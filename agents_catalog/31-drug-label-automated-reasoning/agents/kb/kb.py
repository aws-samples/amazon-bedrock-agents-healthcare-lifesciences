# Strands AgentCore example with Kendra GenAI retrieve tool.
# # To test locally, run `uv run agent.py` and then
# curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt": "What tools do you have?"}'
# curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt": "Can I use anydrug to treat my back pain?"}'

import argparse
import boto3
import asyncio
import datetime
import json
import logging


from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel
from strands.types.content import Message

from datetime import date, datetime
import time

import retrieve

# Configure the root logger to handle  messages
logging.basicConfig(
    level=logging.WARNING,  # Set the root logger level
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
)

# Configure the strands logger
logging.getLogger("strands").setLevel(logging.DEBUG)

model_id = "us.amazon.nova-pro-v1:0"

model = BedrockModel(
    model_id=model_id,
    temperature=0.1,
)

SYSTEM_PROMPT = f"""
# Drug label Assistant

## Overview

You are an AI assistant powered by a large language model. Your primary goal is to answer user questions about pharmaceutical drugs accurately. Do do this, you retrieve information from the drug labels using the `retrieve` tool.

## Current Date

The current date is {date.today().strftime('%Y-%m-%d')}

## Workflow

1. **Assess the request**  
   - If the user asks for factual information, instructions, troubleshooting steps, or any detail that may be covered in a drug label, you **must** first use the `retrieve` tool to get relevant information.  
   - If the user only greets you or makes small talk do **not** use the retrieve tool.

2. **Retrieve**  
   Use the `retrieve` tool with the query text and then wait for the tool’s response before continuing.

3. **Compose the answer**

After using the `retrieve` tool (or if no retrieval was required), write a clear, concise answer of no more than 100 words.

## Safety & style

- Do not request or ask for any personally identifiable information (PII).
- Keep the tone friendly, professional, and to the point.
- If the retrieved material does not contain enough information, say so rather than guessing.

## Example

User: “Hello!”
Assistant: Hello! How can I help you today?
User: “Is drug X approved to treat my stomach ache?”
Assistant: <Calls retrieve tool with "drug X approved to treat my stomach ache">
Assistant (after the tool returns relevant passages): 

Yes, drug X may be used to treat stomach pain
"""

agent = Agent(
    model=model,
    tools=[retrieve],
    system_prompt=SYSTEM_PROMPT,
)


app = BedrockAgentCoreApp()
logging.info(f"Agent ready at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}")


@app.entrypoint
async def main(payload):
    """
    Invoke the agent with a payload
    """

    user_input = payload.get("prompt")
    agent_stream = agent.stream_async(user_input)
    tool_name = None
    try:
        async for event in agent_stream:
            logging.debug(event)

            if (
                "current_tool_use" in event
                and event["current_tool_use"].get("name") != tool_name
            ):
                tool_name = event["current_tool_use"]["name"]
                yield f"\n\n🔧 Using tool: {tool_name}\n\n"

            elif "data" in event:
                tool_name = None
                yield event["data"]

    except Exception as e:
        yield f"Error: {str(e)}"


if __name__ == "__main__":
    app.run()
