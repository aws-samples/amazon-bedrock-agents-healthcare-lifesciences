# AgentCore Gateway MCP Servers

MCP endpoints powered by AWS Lambda tools deployed behind Amazon Bedrock AgentCore Gateway. You deploy CloudFormation stacks to your AWS account and get a secured, authenticated MCP endpoint accessible from any MCP client.

## How It Works

```
Your AI Assistant (Claude Code, Q Desktop, etc.)
    │
    │ MCP protocol (HTTP + JWT auth)
    │
    ▼
AgentCore Gateway (MCP endpoint)
    │
    │ Invokes Lambda targets
    │
    ▼
Lambda Functions (your domain tools)
```

AgentCore Gateway:
- Exposes tools as an MCP server (any MCP client can connect)
- Handles authentication (Cognito OAuth2 / custom JWT)
- Provides semantic tool discovery
- Manages IAM role assumption for Lambda invocation

## Available Servers

| Server | Tools | Domain |
|--------|-------|--------|
| [biomni-research-tools](biomni-research-tools/) | 30+ | Biomedical database queries (UniProt, Reactome, STRING, DrugBank, etc.) |

## Deployment Pattern

Each server deploys 3 CloudFormation stacks:
1. **Infrastructure** — Lambda functions + IAM roles
2. **Cognito** — User pool + OAuth2 clients for authentication
3. **AgentCore** — Gateway + targets + memory

After deployment, you get an MCP endpoint URL that any client can connect to with a JWT token.

## Source Pattern

The deployment pattern is derived from [Agent 28 (Research/Biomni Gateway)](../../agents_catalog/28-Research-agent-biomni-gateway-tools/) in this repository. See that agent's README for the full production implementation with agent runtime, observability, and Streamlit UI.
