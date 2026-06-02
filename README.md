# Healthcare and Life Sciences Agents Toolkit on AWS

A library of healthcare and life sciences domain capabilities — reference agents with best practices, reusable skills, and MCP-based tools — serving builders in their IDEs, researchers in Amazon Quick, and developers deploying to AWS.

> **Note:** This repository is being repositioned to expose HCLS domain capabilities as portable skills and MCP tools across AI coding assistants and end-user platforms, alongside the existing agent catalog. See the [framework design](docs/proposals/framework-design.md) for technical details.

## Overview

The HCLS Agents Toolkit provides domain-specific AI capabilities for healthcare and life sciences workflows on AWS. The catalog of 36+ reference agents is being decomposed into individual skills (domain knowledge) and MCP servers (domain tools) — making the same capabilities accessible across multiple consumption paths without requiring full agent deployment:

| Path | Who | How |
|------|-----|-----|
| **AI Coding Assistants** (Claude Code, Kiro, Codex) | Developers building HCLS agents | Install skills + connect MCP servers |
| **End-User Platforms** (Amazon Quick, Claude Co-work) | Researchers, clinicians, scientists | Connect to HCLS MCP tools via natural language |
| **Agent Deployments** (Amazon Bedrock AgentCore) | Platform teams, operations | Deploy reference agents with best practices |

---

## Toolkit Components

### Agents Catalog

Library of 36+ specialized reference agents spanning drug research, clinical trials, genomics, and commercialization. Each agent demonstrates best practices for building with the [Strands](https://strandsagents.com/) framework and deploying to [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/).

**[agents_catalog/](agents_catalog/)**

Highlights:
- [Research agent with 30+ Biomni database tools](agents_catalog/28-Research-agent-biomni-gateway-tools/) — AgentCore Gateway + Runtime
- [Variant interpreter with HealthOmics](agents_catalog/17-variant-interpreter-agent/) — Genomics at scale
- [Terminology agent with OLS](agents_catalog/35-Terminology-agent/) — Ontology standardization
- [C4LS agent with AgentSkills](agents_catalog/36-C4LS-agent/) — Skills + MCP at runtime

### Step 1: Deploy Shared Infrastructure (if needed)

Some agents require backend infrastructure (Redshift, Bedrock Knowledge Base). Deploy the shared prerequisites stack first:

```bash
aws cloudformation deploy \
  --template-file Infra_cfn.yaml \
  --stack-name hcls-agent-infra \
  --parameter-overrides RedshiftPassword=<YourSecurePassword> \
  --capabilities CAPABILITY_IAM
```

This creates: VPC, Redshift cluster, S3 data bucket, Bedrock Knowledge Base, and an AgentCore execution role. You can also provide an existing VPC via the `ExistingVpcId` parameter.

### Step 2: Deploy an Agent

### MCP Servers

Domain tools exposed as MCP endpoints, organized by deployment model:

**[mcp-servers/](mcp-servers/)**

| Category | What it provides | Example |
|----------|-----------------|---------|
| `agentcore-gateway/` | Deploy CloudFormation → MCP endpoint via AgentCore Gateway | Biomni (30+ biomedical databases) |
| `agentcore-runtime/` | Deploy MCP server container to AgentCore Runtime | OLS (200+ ontologies) |
| `aws-public/` | Pre-existing AWS MCP servers (no deploy) | AWS Knowledge, HealthOmics |
| `third-party/` | Pre-existing public servers (no deploy) | PubMed, Open Targets |

### Skills

Portable domain knowledge that teaches AI assistants how to accomplish HCLS workflows. Skills reference MCP servers by name and describe queries in natural language — no hardcoded tool names.

**[skills/](skills/)**

| Domain | Skills |
|--------|--------|
| Genomics | Variant interpretation, single-cell QC, HealthOmics workflows |
| Drug Discovery | Target identification, compound optimization, safety signals, drug labels |
| Clinical Trials | Trial search, protocol generation, enrollment monitoring |
| Biomarkers | Database analysis, multi-agent discovery, pathway analysis |
| Research | Biomedical databases, deep literature review |
| Terminology | Ontology lookup, data harmonization |

### Platform Guides

Per-platform setup instructions to connect skills and MCP servers to your preferred AI tool.

**[platforms/](platforms/)**

| Platform | Guide |
|----------|-------|
| Claude Code | [platforms/claude-code/](platforms/claude-code/) |
| Amazon Quick | [platforms/amazon-quick/](platforms/amazon-quick/) |
| Kiro | [platforms/kiro/](platforms/kiro/) |

---

## Quick Start

### For Developers (Claude Code / Kiro)

```bash
# 1. Clone the repo
git clone https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences.git
cd amazon-bedrock-agents-healthcare-lifesciences

# 2. Follow platform-specific setup
cat platforms/claude-code/README.md   # or platforms/kiro/
```

Setup installs HCLS skills, connects MCP servers, and enables natural language queries like:

> "Look up human insulin protein and give me the UniProt ID"
> "What diseases are associated with EGFR?"
> "What are the children of seizure (HP:0001250) in HPO?"

For building and deploying agents on AWS, pair this with the [AWS Agent Toolkit](https://github.com/aws/agent-toolkit-for-aws) — it provides generic infrastructure skills (scaffolding, IAM, deployment, debugging) while this toolkit provides the domain-specific knowledge and tools for healthcare and life sciences.

### For Researchers (Amazon Quick)

Connect HCLS MCP servers directly in **Settings > Capabilities > Add MCP Server**. See [platforms/amazon-quick/](platforms/amazon-quick/) for setup.

### For Agent Deployments

Use `agentcore_template/` as your starting point and `agents_catalog/28-Research-agent-biomni-gateway-tools/` as your reference implementation.

```bash
cd agentcore_template
python -m venv .venv && source .venv/bin/activate
uv pip install -r dev-requirements.txt
./scripts/prereq.sh
```

See the [AgentCore template](agentcore_template/) for full deployment instructions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CONSUMPTION SURFACES                                                    │
│  Claude Code · Kiro · Codex · Amazon Quick · Claude Co-work             │
│                                                                          │
│  Skills loaded as context  +  MCP servers connected as tools            │
├─────────────────────────────────────────────────────────────────────────┤
│  PORTABLE INTERFACE LAYER                                                │
│                                                                          │
│  skills/          → Domain knowledge (SKILL.md + scripts + references)  │
│  mcp-servers/     → Domain tools (Gateway, Runtime, public, 3rd-party)  │
│  platforms/       → Per-tool configs and setup guides                    │
├─────────────────────────────────────────────────────────────────────────┤
│  PRODUCTION RUNTIME (Amazon Bedrock AgentCore)                           │
│                                                                          │
│  agents_catalog/  → 36+ reference agents with best practices            │
│  agentcore_template/ → End-to-end deployment template                   │
│  multi_agent_collaboration/ → Multi-agent workflow patterns              │
│  evaluations/     → Agent performance assessment                         │
└─────────────────────────────────────────────────────────────────────────┘
```

The portable interface layer makes catalog agent capabilities consumable across all surfaces — without deploying anything. The reference agents demonstrate best practices for scale, compliance, and determinism.

---

## Kiro Power for Agent Development

This repository includes a Kiro Power to guide you through building AgentCore agents.

**Location:** `powers/hcls-agentcore-builder/`

See [powers/hcls-agentcore-builder/](powers/hcls-agentcore-builder/) for installation instructions.

---

## Contributing

Follow the guidelines to contribute a new agent: **[add-a-new-agent](https://aws-samples.github.io/amazon-bedrock-agents-healthcare-lifesciences/guides/)**

1. Fork the repository and create a branch
2. Use `agentcore_template/` as your starting point for new agents
3. Add to `agents_catalog/` following naming: `<two-digit-index>-<Agent-Name>`
4. Include a README.md describing the agent and deployment steps
5. Open a pull request to `main`

---

## License

This project is licensed under the MIT-0 License.

## Legal Notes

**Important**: This solution is for demonstrative purposes only. It is not for clinical use and is not a substitute for professional medical advice, diagnosis, or treatment. The associated notebooks, including trained models and sample data, are not intended for production. It is each customer's responsibility to determine whether they are subject to HIPAA, and if so, how best to comply with HIPAA and its implementing regulations. Before using AWS in connection with protected health information, customers must enter an AWS Business Associate Addendum (BAA) and follow its configuration requirements.
