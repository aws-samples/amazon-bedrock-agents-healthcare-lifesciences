# Tavily Web Search Agent — AgentCore Gateway Pattern

This is an alternative deployment of the Tavily Web Search agent that uses **AgentCore Gateway + external MCP server** instead of local `@tool` functions.

## Architecture

```
Agent (Strands)  →  AgentCore Gateway  →  Tavily MCP Server (external)
                         │
                    Cedar Policies
                    (tool access control)
```

**Key difference from `agentcore/`:**
- `agentcore/` — tools are local Python functions with `requests` calls and API keys in env vars
- `agentcore-gateway/` — tools are discovered via MCP protocol from an external server; agent code has zero API knowledge

## Setup

```bash
# 1. Initialize project
npx @aws/agentcore create --framework strands --name tavily-web-search

# 2. Add a gateway
npx @aws/agentcore add gateway --name TavilyGateway

# 3. Connect the Tavily MCP server as a gateway target
npx @aws/agentcore add gateway-target \
  --type mcp-server \
  --name TavilySearch \
  --endpoint https://mcp.tavily.com/mcp \
  --gateway TavilyGateway

# 4. Deploy
npx @aws/agentcore deploy -y

# 5. Test
npx @aws/agentcore invoke '{"prompt": "What are the latest developments in mRNA therapeutics?"}'
```

## When to use this pattern

- You want **tool access control** (Cedar policies can allow/deny specific tools per user)
- You want **zero secrets in agent code** (credentials managed by Gateway's credential providers)
- You want to **swap or add tools without code changes** (just `npx @aws/agentcore add gateway-target`)
- You're connecting to a **third-party MCP server** that already exists

## When to use the local `@tool` pattern instead

- The MCP server doesn't exist yet (you'd have to build it)
- Latency is critical and the extra Gateway hop matters
- You need custom pre/post-processing of tool results
- Local development without AWS connectivity
