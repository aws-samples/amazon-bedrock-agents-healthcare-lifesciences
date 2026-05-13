# AgentCore Documentation MCP Server

Local MCP server providing Amazon Bedrock AgentCore API reference and documentation.

## Prerequisites

- [uv](https://astral.sh/uv) installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

```json
{
  "mcpServers": {
    "agentcore-docs": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"]
    }
  }
}
```

## Capabilities

- AgentCore Gateway, Runtime, Memory, Identity API reference
- Configuration and deployment guidance
- SDK usage examples

## Source

Package: [awslabs.amazon-bedrock-agentcore-mcp-server](https://pypi.org/project/awslabs.amazon-bedrock-agentcore-mcp-server/)
