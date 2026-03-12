from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

# ExaAI provides information about code through web searches, crawling and code context searches through their platform. Requires no authentication
# OPENTARGETS_MCP_ENDPOINT = "https://mcp.exa.ai/mcp"

def get_streamable_http_mcp_client(endpoint:str) -> MCPClient:
    """
    Returns an MCP Client compatible with Strands
    """
    # to use an MCP server that supports bearer authentication, add headers={"Authorization": f"Bearer {access_token}"}
    return MCPClient(lambda: streamablehttp_client(endpoint))