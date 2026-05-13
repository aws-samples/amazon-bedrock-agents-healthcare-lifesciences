# HCLS Agents Plugin

Healthcare and Life Sciences domain skills and MCP tools for AI coding assistants.

## What This Plugin Provides

- **Domain skills** — workflow guidance for genomics, drug discovery, clinical trials, biomarker analysis, medical terminology, and more
- **MCP tools** — connections to biomedical databases, ontology services, literature search, and genomics platforms
- **Agent patterns** — references to 36+ production-ready HCLS agents in the catalog

## Installation

### Claude Code

```bash
/plugin marketplace add aws-samples/amazon-bedrock-agents-healthcare-lifesciences
/plugin install hcls-agents
```

### Codex

```bash
codex plugin marketplace add aws-samples/amazon-bedrock-agents-healthcare-lifesciences
codex plugin install hcls-agents
```

### Kiro, Cursor, Q Desktop

See `platforms/` for per-tool setup instructions, or run:

```bash
./platforms/setup.sh
```

## Use With AWS Agent Toolkit

This plugin provides **domain knowledge** (WHAT to build for healthcare/life sciences). For **infrastructure skills** (HOW to deploy on AWS), install the [AWS Agent Toolkit](https://github.com/aws/agent-toolkit-for-aws) alongside:

```bash
/plugin marketplace add aws/agent-toolkit-for-aws
/plugin install aws-agents
```

Together:
- HCLS skills guide domain workflows (variant interpretation, trial matching, biomarker analysis)
- AWS Agent Toolkit skills handle infrastructure (deploy to AgentCore, create IAM roles, configure guardrails)
- AWS MCP servers execute infrastructure actions when HCLS skills need them (HealthOmics for genomics, Athena for data, S3 for storage)

## MCP Servers Included

The default `.mcp.json` connects to:
- **AWS Knowledge** — AWS documentation and architecture guidance
- **AgentCore Docs** — Bedrock AgentCore API reference
- **Strands Docs** — Strands Agents SDK documentation
- **AWS HealthOmics** — 60+ genomics workflow management tools

Additional MCP servers (biomedical databases, ontologies, literature) are available in `mcp-servers/` — see their READMEs for setup.

## Skills

Skills are located in the top-level `skills/` directory. Each skill contains:
- `SKILL.md` — workflow instructions with YAML frontmatter
- `scripts/` — executable code the AI assistant can run
- `references/` — domain documentation loaded on-demand

See `skills/` for the full catalog of available skills.
