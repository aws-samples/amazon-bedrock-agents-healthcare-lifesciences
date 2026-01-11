from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import os


def _invoke_agent(
    bedrock_model,
    mcp_client,
    prompt
):
    with mcp_client:
        tools = mcp_client.list_tools_sync()
        agent = Agent(
            model=bedrock_model,
            tools=tools
        )
        return agent(prompt)


def _create_streamable_http_transport(headers=None):
    url = "https://sila2-gateway-1764211277-oenso7x7wz.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp"
    access_token = os.environ.get("ACCESS_TOKEN")
    if not access_token:
        raise ValueError("ACCESS_TOKEN environment variable is required")
    headers = {**headers} if headers else {}
    headers["Authorization"] = f"Bearer {access_token}"
    return streamablehttp_client(
        url,
        headers=headers
    )

def _get_bedrock_model(model_id):
    return BedrockModel(
        inference_profile_id=model_id,
        temperature=0.0,
        streaming=True,
   )

mcp_client = MCPClient(_create_streamable_http_transport)

if __name__ == "__main__":
    user_prompt = "What orders do I have?"
    _response = _invoke_agent(
        bedrock_model=_get_bedrock_model("us.anthropic.claude-sonnet-4-20250514-v1:0"),
        mcp_client=mcp_client,
        prompt=user_prompt
    )
    print(_response)
