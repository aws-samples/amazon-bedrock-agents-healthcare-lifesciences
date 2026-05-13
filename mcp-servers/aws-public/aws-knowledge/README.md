# AWS Knowledge MCP Server

Remote HTTP MCP server providing AWS documentation search and architecture guidance. No local installation needed.

## Setup

Add to your assistant's MCP configuration:

```json
{
  "mcpServers": {
    "awsknowledge": {
      "type": "http",
      "url": "https://knowledge-mcp.global.api.aws"
    }
  }
}
```

## Capabilities

- Search AWS documentation across all services
- Architecture guidance and best practices
- No authentication required

## Source

Part of the [AWS Agent Toolkit](https://github.com/aws/agent-toolkit-for-aws) (aws-agents plugin).
