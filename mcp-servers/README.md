# MCP Servers

MCP (Model Context Protocol) servers provide domain tools accessible from any MCP-compatible client — AI coding assistants (Claude Code, Kiro, Codex, Cursor), end-user platforms (Amazon Q Desktop, Claude Co-work), and production agents.

## Categories

### [agentcore-gateway/](agentcore-gateway/) — User Deploys

MCP endpoints powered by AWS Lambda tools behind AgentCore Gateway. You deploy CloudFormation stacks to your AWS account and get a secured MCP endpoint.

| Server | Tools | What it provides |
|--------|-------|------------------|
| [biomni-research-tools](agentcore-gateway/biomni-research-tools/) | 30+ | Biomedical database queries (UniProt, Reactome, STRING, DrugBank, etc.) |

### [agentcore-runtime/](agentcore-runtime/) — User Deploys

Custom MCP servers deployed as containers on AgentCore Runtime. You build and deploy to get a hosted MCP server.

| Server | Tools | What it provides |
|--------|-------|------------------|
| [ontology-lookup-service](agentcore-runtime/ontology-lookup-service/) | 7 | Medical/biological terminology standardization across 200+ EBI ontologies |

### [aws-public/](aws-public/) — User Configures

Existing AWS-published MCP servers. No deployment needed — add the config to your assistant.

| Server | Transport | What it provides |
|--------|-----------|------------------|
| [aws-healthomics](aws-public/aws-healthomics/) | stdio (local) | 60+ HealthOmics workflow, run, and data store management tools |
| [aws-knowledge](aws-public/aws-knowledge/) | HTTP (remote) | AWS documentation search and architecture guidance |
| [agentcore-docs](aws-public/agentcore-docs/) | stdio (local) | AgentCore API reference and documentation |
| [strands-docs](aws-public/strands-docs/) | stdio (local) | Strands Agents SDK documentation |
| [aws-mcp](aws-public/aws-mcp/) | stdio (local) | 300+ AWS service operations (from AWS Agent Toolkit) |

### [third-party/](third-party/) — User Configures

Public third-party MCP servers for life sciences. No deployment needed — add the config to your assistant.

| Server | Transport | Provider | What it provides |
|--------|-----------|----------|------------------|
| [pubmed](third-party/pubmed/) | HTTP | NLM | Biomedical literature search |
| [open-targets](third-party/open-targets/) | HTTP | Open Targets | Gene-disease associations, drug targets |
| [chembl](third-party/chembl/) | HTTP | deepsense.ai | Chemical compound data |
| [clinical-trials](third-party/clinical-trials/) | HTTP | deepsense.ai | ClinicalTrials.gov search |
| [biorxiv](third-party/biorxiv/) | HTTP | deepsense.ai | Preprint literature |
| [synapse](third-party/synapse/) | HTTP | Sage Bionetworks | Collaborative research data |
| [biorender](third-party/biorender/) | HTTP | BioRender | Scientific figure creation |
| [consensus](third-party/consensus/) | HTTP | Consensus | Evidence-based answers from papers |
| [cortellis](third-party/cortellis/) | HTTP | Clarivate | Regulatory intelligence |
| [adisinsight](third-party/adisinsight/) | HTTP | Springer Nature | Drug pipeline data |
| [medidata](third-party/medidata/) | HTTP | Medidata | Clinical trial data platform |
| [wiley](third-party/wiley/) | HTTP | Wiley | Academic literature |
| [owkin](third-party/owkin/) | HTTP | Owkin | AI-powered biomarkers |
| [10x-genomics](third-party/10x-genomics/) | MCPB (local) | 10x Genomics | Single-cell genomics |
| [tooluniverse](third-party/tooluniverse/) | MCPB (local) | MIMS Harvard | Bioinformatics tool discovery |

## How Skills Use MCP Servers

HCLS skills define **domain workflows**. When those workflows need tool execution, the skill instructs the AI assistant to call the appropriate MCP server:

```
Skill: genomics-variant-interpretation
  Step 1: "Use aws-healthomics MCP to retrieve the VCF from HealthOmics"
  Step 2: "Use open-targets MCP to check gene-disease associations"
  Step 3: "Use pubmed MCP to find supporting literature"
  Step 4: "Generate clinical interpretation report"
```

No agent deployment needed — skills + MCP servers work directly in the user's coding assistant or Q Desktop.
