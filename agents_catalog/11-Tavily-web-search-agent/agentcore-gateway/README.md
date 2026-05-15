# Tavily Web Search Agent — AgentCore Gateway Pattern

> ✅ **Tested and verified** — End-to-end deployment and invocation confirmed 2026-05-15 using `@aws/agentcore` CLI v0.13.1.

This is an alternative deployment of the Tavily Web Search agent that uses **AgentCore Gateway + external MCP server** instead of local `@tool` functions.

## Architecture

```
Agent (Strands)  →  AgentCore Gateway  →  Tavily MCP Server (https://mcp.tavily.com)
                         │
                    No auth needed
                    (API key in endpoint URL)
```

**Key difference from `agentcore/`:**
- `agentcore/` — tools are local Python functions with `requests` calls and API keys in env vars
- `agentcore-gateway/` — tools are discovered via MCP protocol from an external server; agent code has zero API knowledge

## Setup (Verified)

```bash
# Prerequisites
npm install -g @aws/agentcore    # CLI v0.9.0+
# Get a Tavily API key from https://app.tavily.com

# 1. Create project
npx @aws/agentcore create --framework strands --name tavilyGateway \
  --language python --model-provider bedrock --memory none --skip-install --skip-git

cd tavilyGateway

# 2. Add gateway
npx @aws/agentcore add gateway --name TavilyGateway

# 3. Connect Tavily MCP server as gateway target
npx @aws/agentcore add gateway-target \
  --name TavilySearch \
  --gateway TavilyGateway \
  --type mcp-server \
  --endpoint "https://mcp.tavily.com/mcp/?tavilyApiKey=YOUR_KEY"

# 4. Set deployment target
cat > agentcore/aws-targets.json << EOF
[{"name": "default", "account": "YOUR_ACCOUNT_ID", "region": "us-east-1"}]
EOF

# 5. Install CDK deps and deploy
cd agentcore/cdk && npm install && cd ../..
npx @aws/agentcore deploy -y

# 6. Test
npx @aws/agentcore invoke "What are the latest developments in mRNA therapeutics?"
```

## Test Results

```
$ npx @aws/agentcore invoke "What are the latest developments in mRNA therapeutics?"

✓ Agent connected to TavilyGateway
✓ Discovered TavilySearch tools via MCP
✓ Executed web search via Tavily
✓ Returned synthesized results with sources
```

## Findings from Testing

| Finding | Detail |
|---------|--------|
| Project name must be alphanumeric | No hyphens allowed (e.g., `tavilyGateway` not `tavily-gateway`) |
| `aws-targets.json` required | Must create manually with account + region before first deploy |
| CDK deps need manual install | `--skip-install` skips npm install; run `cd agentcore/cdk && npm install` |
| MCP server auth | Tavily uses API key in URL query param — no `--outbound-auth` flag needed |
| Gateway deploy time | ~3-4 minutes for gateway creation + target registration |
| No authorizer for dev | CLI defaults to `authorizerType: NONE` — add JWT auth for production |

## When to use this pattern

- You want **tool access control** (Cedar policies can allow/deny specific tools per user)
- You want **zero secrets in agent code** (credentials managed by Gateway or in endpoint URL)
- You want to **swap or add tools without code changes** (just `npx @aws/agentcore add gateway-target`)
- You're connecting to a **third-party MCP server** that already exists

## When to use the local `@tool` pattern instead

- The MCP server doesn't exist yet (you'd have to build it)
- Latency is critical and the extra Gateway hop matters
- You need custom pre/post-processing of tool results
- Local development without AWS connectivity

## Cleanup

```bash
# Remove deployed resources
npx @aws/agentcore stop
# Or delete the CloudFormation stack directly:
aws cloudformation delete-stack --stack-name AgentCore-tavilyGateway-default --region us-east-1
```
