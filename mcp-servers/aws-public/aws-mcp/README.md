# AWS MCP Server

Local stdio proxy to the AWS MCP server providing authenticated access to 300+ AWS services, documentation search, and sandboxed script execution.

## Prerequisites

- AWS credentials configured (`aws configure`)
- [uv](https://astral.sh/uv) installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

```json
{
  "mcpServers": {
    "aws-mcp": {
      "command": "uvx",
      "args": ["mcp-proxy-for-aws@latest", "https://aws-mcp.us-east-1.api.aws/mcp"]
    }
  }
}
```

## Capabilities

- `search_documentation` — search AWS docs (no auth required)
- `retrieve_skill` — discover and load AWS skills on demand
- `call_aws` — authenticated access to 300+ AWS services (IAM, S3, Lambda, Athena, etc.)
- `run_script` — sandboxed Python script execution

## When HCLS Skills Use This

HCLS domain skills reference this MCP server when they need AWS infrastructure actions:
- Deploy CloudFormation stacks for agent infrastructure
- Create/invoke Lambda functions for tool handlers
- Query Athena for data processing
- Manage S3 buckets for data storage
- Configure IAM roles for agent permissions

## Source

Part of the [AWS Agent Toolkit](https://github.com/aws/agent-toolkit-for-aws) (aws-core plugin).
