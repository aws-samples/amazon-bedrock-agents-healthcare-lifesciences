# Clinical Study Research Agent — AgentCore Gateway Pattern

This is an alternative deployment that connects to **multiple external MCP servers** via AgentCore Gateway, demonstrating how a single agent can aggregate tools from different data sources without any local tool code.

## Architecture

```
Agent (Strands)  →  AgentCore Gateway  →  ClinicalTrials.gov MCP Server
                         │              →  PubMed MCP Server
                         │              →  OpenFDA MCP Server
                         │
                    Cedar Policies
                    (per-tool access control)
```

**What the agent code does:** Connects to the gateway, discovers all available tools, passes them to the Strands Agent. Zero knowledge of which APIs exist or how to call them.

**What the gateway does:** Aggregates tools from all connected MCP servers into a single catalog. Handles outbound auth, rate limiting, and policy enforcement.

## Setup

```bash
# 1. Initialize
npx @aws/agentcore create --framework strands --name clinical-study-research

# 2. Add gateway
npx @aws/agentcore add gateway --name ClinicalResearchGateway

# 3. Connect data sources as MCP server targets
npx @aws/agentcore add gateway-target \
  --type mcp-server \
  --name ClinicalTrials \
  --endpoint https://mcp.clinicaltrials.example.com/mcp \
  --gateway ClinicalResearchGateway

npx @aws/agentcore add gateway-target \
  --type mcp-server \
  --name PubMed \
  --endpoint https://mcp.pubmed.example.com/mcp \
  --gateway ClinicalResearchGateway

npx @aws/agentcore add gateway-target \
  --type mcp-server \
  --name OpenFDA \
  --endpoint https://mcp.openfda.example.com/mcp \
  --gateway ClinicalResearchGateway

# 4. Deploy
npx @aws/agentcore deploy -y

# 5. Test
npx @aws/agentcore invoke '{"prompt": "Find active Phase 3 trials for NSCLC with pembrolizumab"}'
```

## Adding a new data source

No code changes needed — just add another gateway target:

```bash
# Example: add UniProt protein data
npx @aws/agentcore add gateway-target \
  --type mcp-server \
  --name UniProt \
  --endpoint https://mcp.uniprot.example.com/mcp \
  --gateway ClinicalResearchGateway

npx @aws/agentcore deploy -y
```

The agent automatically discovers the new tools on next invocation.

## Cedar policy example (restrict tool access)

```cedar
// Only allow clinical-trials-search for users in the "researcher" role
permit(
  principal in Role::"researcher",
  action == Action::"call_tool",
  resource == Tool::"ClinicalTrials::search_trials"
);

// Deny OpenFDA access for non-regulatory users
forbid(
  principal,
  action == Action::"call_tool",
  resource == Tool::"OpenFDA::*"
) unless {
  principal in Role::"regulatory"
};
```

## Example prompts

- "Find active Phase 3 trials for NSCLC with pembrolizumab"
- "What does the literature say about pembrolizumab resistance mechanisms?"
- "Is pembrolizumab FDA-approved for first-line NSCLC?"
- "Compare enrollment across pembrolizumab trials in Europe vs US"

## Comparison: local tools vs gateway

| Aspect | `agentcore/` (local tools) | `agentcore-gateway/` (this) |
|--------|---------------------------|----------------------------|
| API keys | In env vars, agent code handles auth | Gateway manages credentials |
| Adding a tool | Write Python function + redeploy | `npx @aws/agentcore add gateway-target` + redeploy |
| Access control | None (all tools always available) | Cedar policies per tool/user/role |
| Tool discovery | Hardcoded in agent constructor | Dynamic via MCP protocol |
| Code complexity | Higher (HTTP calls, error handling) | Minimal (just connect to gateway) |
| Local dev | Works offline | Needs gateway deployed (or fallback) |
