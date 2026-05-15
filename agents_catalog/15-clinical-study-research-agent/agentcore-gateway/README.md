# Clinical Study Research Agent — AgentCore Gateway Pattern

> ✅ **Tested and verified** — End-to-end deployment and invocation confirmed 2026-05-15 using `@aws/agentcore` CLI v0.13.1. Agent returned real NCT trial data via Tavily MCP → ClinicalTrials.gov.

This is an alternative deployment that connects to **external MCP servers** via AgentCore Gateway, demonstrating how a single agent can aggregate tools from different data sources without any local tool code.

## Architecture

```
Agent (Strands)  →  AgentCore Gateway  →  Tavily MCP Server
                         │                    ↓
                         │              ClinicalTrials.gov
                         │              PubMed
                         │              OpenFDA
                    No auth needed
                    (API key in endpoint URL)
```

**What the agent code does:** Connects to the gateway, discovers all available tools, passes them to the Strands Agent. Zero knowledge of which APIs exist or how to call them.

## Setup (Verified)

```bash
# Prerequisites
npm install -g @aws/agentcore    # CLI v0.9.0+
# Get a Tavily API key from https://app.tavily.com

# 1. Create project
npx @aws/agentcore create --framework strands --name clinicalResearch \
  --language python --model-provider bedrock --memory none --skip-install --skip-git

cd clinicalResearch

# 2. Add gateway
npx @aws/agentcore add gateway --name ClinicalGateway

# 3. Connect Tavily MCP server (searches ClinicalTrials.gov, PubMed, OpenFDA via web)
npx @aws/agentcore add gateway-target \
  --name TavilySearch \
  --gateway ClinicalGateway \
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
npx @aws/agentcore invoke "Find active Phase 3 trials for pembrolizumab in NSCLC"
```

## Test Results

```
$ npx @aws/agentcore invoke "Find active Phase 3 clinical trials for pembrolizumab in non-small cell lung cancer"

✓ Agent connected to ClinicalGateway
✓ Discovered TavilySearch tools via MCP
✓ Searched ClinicalTrials.gov via Tavily
✓ Returned 10 real NCT trials with:
  - NCT IDs (NCT03793179, NCT06312137, NCT05226598, etc.)
  - Trial status (Recruiting, Active)
  - Sponsors (Merck, NCI)
  - Enrollment numbers
  - Primary endpoints and completion dates
```

## Adding more data sources

No code changes needed — just add another gateway target:

```bash
# Example: add a dedicated PubMed MCP server when one becomes available
npx @aws/agentcore add gateway-target \
  --name PubMedSearch \
  --gateway ClinicalGateway \
  --type mcp-server \
  --endpoint "https://your-pubmed-mcp-server.example.com/mcp"

npx @aws/agentcore deploy -y
```

The agent automatically discovers the new tools on next invocation.

## Findings from Testing

| Finding | Detail |
|---------|--------|
| Single MCP server covers multiple sources | Tavily searches ClinicalTrials.gov, PubMed, and OpenFDA via web — no need for separate MCP servers per source |
| Real NCT data returned | Agent found actual trial IDs, not hallucinated data |
| System prompt guides source selection | Adding `site:clinicaltrials.gov` hints in the prompt improves targeting |
| Deploy time | ~4 minutes (gateway + runtime + target) |
| No dedicated clinical trials MCP server needed yet | Tavily's web search is sufficient for discovery; dedicated MCP servers add value for structured queries |

## Future: Multiple dedicated MCP servers

When dedicated MCP servers become available for ClinicalTrials.gov, PubMed, and OpenFDA, the architecture evolves to:

```bash
npx @aws/agentcore add gateway-target --name ClinicalTrials --type mcp-server \
  --endpoint "https://mcp.clinicaltrials.example.com/mcp" --gateway ClinicalGateway

npx @aws/agentcore add gateway-target --name PubMed --type mcp-server \
  --endpoint "https://mcp.pubmed.example.com/mcp" --gateway ClinicalGateway

npx @aws/agentcore add gateway-target --name OpenFDA --type mcp-server \
  --endpoint "https://mcp.openfda.example.com/mcp" --gateway ClinicalGateway
```

Same agent code, same gateway — just more specialized tools available.

## Comparison: local tools vs gateway

| Aspect | `agentcore/` (local tools) | `agentcore-gateway/` (this) |
|--------|---------------------------|----------------------------|
| API keys | In env vars, agent code handles auth | Gateway manages credentials |
| Adding a tool | Write Python function + redeploy | `npx @aws/agentcore add gateway-target` + redeploy |
| Access control | None (all tools always available) | Cedar policies per tool/user/role |
| Tool discovery | Hardcoded in agent constructor | Dynamic via MCP protocol |
| Code complexity | Higher (HTTP calls, error handling) | Minimal (connect to gateway) |
| Local dev | Works offline | Needs gateway deployed (or fallback) |

## Cleanup

```bash
npx @aws/agentcore stop
# Or delete the CloudFormation stack:
aws cloudformation delete-stack --stack-name AgentCore-clinicalResearch-default --region us-east-1
```
