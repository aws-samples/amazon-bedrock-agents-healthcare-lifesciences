# AgentCore Runtime MCP Servers

Custom MCP servers deployed as containers on Amazon Bedrock AgentCore Runtime. You build a Docker image with your MCP server code, deploy to AgentCore Runtime, and get a hosted MCP endpoint.

## How It Works

```
Your AI Assistant (Claude Code, Q Desktop, etc.)
    │
    │ MCP protocol (HTTP + IAM SigV4 auth)
    │
    ▼
AgentCore Runtime (hosts your MCP server container)
    │
    │ Your MCP server code runs inside
    │
    ▼
External APIs (EBI OLS, PubMed, etc.)
```

AgentCore Runtime:
- Hosts your MCP server as a managed container
- Handles scaling, health checks, and observability
- Provides IAM SigV4 authentication
- Integrates with AgentCore Gateway for unified MCP access

## Available Servers

| Server | Tools | Domain |
|--------|-------|--------|
| [ontology-lookup-service](ontology-lookup-service/) | 7 | Medical/biological terminology across 200+ EBI ontologies |

## Source Pattern

The deployment pattern is derived from [Agent 35 (Terminology/OLS)](../../agents_catalog/35-Terminology-agent/) in this repository. See that agent's README for the full production implementation using the FAST template.
