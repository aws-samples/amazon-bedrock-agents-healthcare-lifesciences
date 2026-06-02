# Clinical Study Research Agent — AgentCore Gateway Pattern

> ✅ **Tested and verified** — 2026-05-19 using `@aws/agentcore` CLI v0.13.1 with public PubMed MCP server from [Anthropic life-sciences marketplace](https://github.com/anthropics/life-sciences).

This deployment connects to **public life-sciences MCP servers** via AgentCore Gateway — the same servers used by the Anthropic life-sciences marketplace for Claude Code.

## Architecture

```
Agent (Strands)  →  AgentCore Gateway  →  PubMed MCP Server (pubmed.mcp.claude.com)
                         │              →  Tavily MCP Server (clinical trials via web)
                         │
                    Tools auto-discovered
                    via MCP protocol
```

## MCP Servers Used

| Server | Endpoint | Source | Auth |
|--------|----------|--------|------|
| **PubMed** | `https://pubmed.mcp.claude.com/mcp` | [anthropics/life-sciences](https://github.com/anthropics/life-sciences/tree/main/pubmed) | None (free) |
| **Tavily** | `https://mcp.tavily.com/mcp/?tavilyApiKey=KEY` | [tavily-ai/tavily-mcp](https://github.com/tavily-ai/tavily-mcp) | API key in URL |

## Setup (Verified)

```bash
# Prerequisites
npm install -g @aws/agentcore

# 1. Create project
npx @aws/agentcore create --framework strands --name clinicalMcp \
  --language python --model-provider bedrock --memory none --skip-install --skip-git

cd clinicalMcp

# 2. Add gateway
npx @aws/agentcore add gateway --name ClinicalGateway

# 3. Connect PubMed MCP server (free, no auth — from Anthropic life-sciences)
npx @aws/agentcore add gateway-target \
  --name PubMed \
  --gateway ClinicalGateway \
  --type mcp-server \
  --endpoint "https://pubmed.mcp.claude.com/mcp"

# 4. Connect Tavily for clinical trials web search (optional, needs API key)
npx @aws/agentcore add gateway-target \
  --name TavilySearch \
  --gateway ClinicalGateway \
  --type mcp-server \
  --endpoint "https://mcp.tavily.com/mcp/?tavilyApiKey=YOUR_KEY"

# 5. Set deployment target
cat > agentcore/aws-targets.json << EOF
[{"name": "default", "account": "YOUR_ACCOUNT_ID", "region": "us-east-1"}]
EOF

# 6. Install CDK deps and deploy
cd agentcore/cdk && npm install && cd ../..
npx @aws/agentcore deploy -y

# 7. Test
npx @aws/agentcore invoke "Search PubMed for recent papers on CRISPR gene therapy for sickle cell disease"
```

## Test Results

```
$ npx @aws/agentcore invoke "Search PubMed for recent papers on CRISPR gene therapy for sickle cell disease"

✓ Agent connected to ClinicalGateway
✓ Discovered PubMed + TavilySearch tools via MCP
✓ Searched PubMed via dedicated MCP server
✓ Returned real papers with:
  - Casgevy (exa-cel) FDA approval status
  - Phase 1/2 trial results
  - Safety studies on off-target effects
  - Comparative studies (CRISPR vs base editing vs lentiviral)
  - Long-term follow-up data (up to 13 years)
```

## Other Public Life-Sciences MCP Servers

From [anthropics/life-sciences](https://github.com/anthropics/life-sciences), these can also be added as gateway targets:

| Server | Endpoint | Description |
|--------|----------|-------------|
| ClinicalTrials.gov | `https://mcp.deepsense.ai/clinical_trials/mcp` | NIH clinical trial registry |
| Consensus | Remote MCP | 200M+ peer-reviewed papers |
| Open Targets | Remote MCP | Drug target validation |
| ChEMBL | Remote MCP | Bioactivity data |
| BioRender | Remote MCP | Scientific illustrations |

## Cleanup

```bash
npx @aws/agentcore stop
aws cloudformation delete-stack --stack-name AgentCore-clinicalMcp-default --region us-east-1
```
