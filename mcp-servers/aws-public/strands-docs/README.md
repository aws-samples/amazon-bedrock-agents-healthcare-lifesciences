# Strands Agents Documentation MCP Server

Local MCP server providing Strands Agents SDK documentation and usage guidance.

## Prerequisites

- [uv](https://astral.sh/uv) installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

```json
{
  "mcpServers": {
    "strands-docs": {
      "command": "uvx",
      "args": ["strands-agents-mcp-server"]
    }
  }
}
```

## Capabilities

- Strands Agents SDK API reference
- Tool development patterns
- Agent configuration guidance
- Multi-agent orchestration patterns

## Source

- Package: [strands-agents-mcp-server](https://pypi.org/project/strands-agents-mcp-server/)
- Framework: [strands-agents/sdk-python](https://github.com/strands-agents/sdk-python)
