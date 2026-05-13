# HCLS Agents Toolkit: Framework Design

## Overview

This document describes the design of the skills, MCP servers, plugins, and platform integration framework for the HCLS Agents Toolkit. The framework makes domain capabilities portable across AI coding assistants and end-user platforms while preserving the agent catalog as the production offering.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MARKETPLACE REGISTRATION                                                   │
│  .claude-plugin/marketplace.json  +  .agents/plugins/marketplace.json       │
│  (Makes this repo installable via plugin install mechanisms)                │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│  PLUGIN DEFINITION: plugins/hcls-agents/                                    │
│  • .claude-plugin/plugin.json (Claude Code manifest)                        │
│  • .codex-plugin/plugin.json  (Codex manifest)                              │
│  • .mcp.json                  (default MCP server config)                   │
│  • References skills/ and mcp-servers/                                      │
│  PURPOSE: defines what gets installed — metadata, manifests, default config │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼───────────┐    ┌─────────▼─────────┐    ┌───────────▼──────────┐
│  skills/           │    │  mcp-servers/      │    │  platforms/           │
│  (KNOWLEDGE)       │    │  (TOOLS)           │    │  (ADAPTERS)           │
│                    │    │                    │    │                       │
│  Source of truth   │    │  4 categories:     │    │  Per-tool configs:    │
│  SKILL.md files    │    │  • gateway (deploy)│    │  • claude-code/       │
│  with scripts/     │    │  • runtime (deploy)│    │  • kiro/              │
│  and references/   │    │  • aws-public      │    │  • codex/             │
│                    │    │  • third-party     │    │  • q-desktop/         │
│                    │    │                    │    │  • setup.sh           │
└────────────────────┘    └────────────────────┘    └───────────────────────┘
        │                           │
        │     ┌─────────────────────┘
        │     │
┌───────▼─────▼──────────────────────────────────────────────────────────────┐
│  PRODUCTION AGENTS: agents_catalog/                                         │
│  36+ deployed agent runtimes on AgentCore                                   │
│  • Skills REFERENCE these as implementations                                │
│  • MCP servers may be EXTRACTED from these                                  │
│  • Agents CONSUME skills + MCP tools at runtime                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration with AWS Agent Toolkit (No Replication)

The [AWS Agent Toolkit](https://github.com/aws/agent-toolkit-for-aws) provides generic AWS infrastructure skills and MCP servers. **We do not replicate any of its content.** Instead, we position as a complementary domain layer:

```
┌─────────────────────────────────────────────────────────────────┐
│  User's AI Coding Assistant (Claude Code, Kiro, Codex, etc.)    │
│                                                                  │
│  Installed plugins:                                              │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │ AWS Agent Toolkit     │    │ HCLS Agents Toolkit           │  │
│  │ (generic infra HOW)   │    │ (domain-specific WHAT)        │  │
│  │                       │    │                               │  │
│  │ • aws-agents skills   │    │ • HCLS domain skills          │  │
│  │ • aws-core skills     │    │ • HCLS MCP servers            │  │
│  │ • aws-data-analytics  │    │ • Agent catalog references    │  │
│  │ • AWS MCP server      │    │ • Domain workflows            │  │
│  └───────────┬───────────┘    └───────────────┬───────────────┘  │
│              │                                 │                  │
│              │    Skills reference AWS MCP     │                  │
│              │◄───servers when they need────────┘                  │
│              │    infrastructure actions                          │
└──────────────┼───────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  AWS MCP Servers (infrastructure execution layer)               │
│                                                                  │
│  • aws-mcp (300+ services)     — general infra operations       │
│  • aws-healthomics-mcp-server  — genomics workflow execution    │
│  • aws-athena-mcp-server       — data processing/queries        │
│  • agentcore-mcp-server        — AgentCore API documentation    │
│  • strands-agents-mcp-server   — Strands framework docs         │
│                                                                  │
│  These are NOT part of this repo — users install/configure them  │
└─────────────────────────────────────────────────────────────────┘
```

**Key principle:** HCLS skills define domain workflows. When those workflows need to interact with AWS infrastructure, the skill instructs the AI assistant to use the appropriate AWS MCP server:

| HCLS skill action | AWS MCP server used | Example |
|-------------------|--------------------|---------| 
| Run a genomics workflow | `aws-healthomics-mcp-server` | "Start a variant calling workflow on HealthOmics" |
| Query clinical data in S3 Tables | `aws-mcp` (Athena) | "Query the biomarker table for NSCLC patients" |
| Deploy an agent to AgentCore | `aws-mcp` or `agentcore-mcp-server` | "Deploy this agent to AgentCore Runtime" |
| Create IAM roles for an agent | `aws-mcp` (IAM) | "Create execution role with Bedrock invoke permissions" |
| Store results in S3 | `aws-mcp` (S3) | "Upload the analysis report to the results bucket" |

**What this means for users:**
1. Install HCLS plugin → domain skills and HCLS-specific MCP servers load into their assistant
2. Optionally install AWS Agent Toolkit → generic infra skills load alongside
3. Both work independently; together they cover the full build-and-deploy workflow
4. HCLS skills and MCP servers are usable in Claude Code, Kiro, Q Desktop, Co-work without deploying any agent — they work standalone

---

## Layer Responsibilities

### plugins/hcls-agents/ — "What is installable"

The plugin definition registers this repo as an installable package in AI coding assistant marketplaces. When a developer runs `/plugin install hcls-agents@amazon-bedrock-agents-healthcare-lifesciences`, this is what gets loaded.

**Contains:**
- Marketplace manifests (Claude Code + Codex formats)
- Default `.mcp.json` with all configurable MCP servers
- README with usage instructions
- Pointers to skills (which get loaded into the assistant's context)

**Does NOT contain:** Skill content itself, platform-specific configs, or agent code.

### skills/ — "Domain knowledge"

The canonical source of all HCLS workflow knowledge. Each skill teaches an AI coding assistant (or end-user platform) how to accomplish a specific HCLS task.

**Each skill:**
```
skills/<skill-name>/
├── SKILL.md          ← Instructions (YAML frontmatter + markdown body)
├── scripts/          ← Executable code the AI runs (Python, bash)
└── references/       ← Domain docs loaded on-demand for context
```

Skills are consumed by:
- Claude Code (via plugin install → loads SKILL.md)
- Kiro (adapted to POWER.md + steering/ format in platforms/kiro/)
- Codex (via .codex-plugin → skills path)
- Q Desktop (copied to ~/.quickwork/skills/)
- Production agents (via Strands AgentSkills at runtime)
- AgentCore Registry (registered as AGENT_SKILLS records)

### mcp-servers/ — "Domain tools"

MCP server configurations and deployable server code, organized by deployment model.

| Category | User action | Example |
|----------|-------------|---------|
| `agentcore-gateway/` | Deploys CloudFormation stacks → gets MCP endpoint | Biomni 30+ database tools |
| `agentcore-runtime/` | Deploys MCP server container to Runtime | OLS ontology lookup |
| `aws-public/` | Configures existing AWS MCP servers (no deploy) | HealthOmics, AWS Knowledge, AgentCore docs |
| `third-party/` | Configures existing third-party servers (no deploy) | PubMed, OpenTargets, ChEMBL, BioRxiv |

### platforms/ — "How to install per tool"

Per-coding-assistant configuration adapters. Takes the same skills and MCP servers and packages them in each tool's expected format.

Follows the pattern from `sample-healthomics-agentic-setup`:
- One folder per platform with ready-to-use config files
- Interactive `setup.sh` that asks which platform and installs appropriately
- Shared content, different packaging

### agents_catalog/ — "Production products"

Unchanged. The 36+ production agents remain the core offering. The framework layers above make these agents:
- **Discoverable** — skills describe what they do and when to use them
- **Accessible** — MCP servers expose their tools to any client
- **Composable** — Registry records enable dynamic multi-agent orchestration
- **Buildable** — skills teach developers how to create similar agents

---

## Relationship Between Layers

```
Developer installs plugin
  → Skills load into their coding assistant
  → MCP servers connect to domain tools
  → Developer builds a new HCLS agent guided by skills, using MCP tools
  → Deploys to AgentCore (becomes a new catalog agent)

Researcher connects MCP servers to Q Desktop
  → Gets 30+ biomedical database tools via natural language
  → Skills guide complex multi-step workflows
  → No agent deployment needed

Platform team deploys catalog agents
  → Agents register in AgentCore Registry
  → Orchestrator discovers them dynamically
  → Multi-agent workflows compose at runtime
```

---

## Skills Proposal

Based on analysis of 36+ catalog agents, 4 multi-agent workflows, and 7 target identification agents, the following skills are proposed organized by category.

### Category 1: Builder Skills (meta — how to build HCLS agents)

| Skill | What it teaches | References |
|-------|----------------|------------|
| `hcls-get-started` | Orient a developer in this toolkit: what's available, how to choose a pattern, first steps | All agent READMEs, agentcore_template/ |
| `hcls-build-agent` | Structure an HCLS agent: tools, system prompts, domain knowledge, guardrails | agentcore_template/, agent 28, agent 35 |
| `hcls-deploy-agent` | Deploy to AgentCore: Gateway, Runtime, Memory, Identity, Registry | Deployment scripts, FAST template |
| `hcls-add-mcp-tools` | Add MCP tools to an agent: Gateway targets, Lambda handlers, API specs | Agent 28 gateway pattern |
| `hcls-domain-conventions` | HCLS data formats, ontologies, PHI handling, compliance requirements | Cross-agent patterns |

### Category 2: Genomics & Variant Analysis

| Skill | What it teaches | Source agents |
|-------|----------------|--------------|
| `genomics-variant-interpretation` | Interpret VCF files: annotation, pathogenicity classification, clinical reporting | Agent 17 (Variant Interpreter), Kiro genetic-risk-assessment |
| `genomics-single-cell-qc` | QC single-cell RNA-seq: Cell Ranger metrics, quality thresholds, pass/fail decisions | Agent 20 (Single Cell QC), life-sciences/single-cell-rna-qc |
| `genomics-healthomics-workflows` | Run genomic workflows on AWS HealthOmics: WDL/Nextflow, batch processing | Agent 08 (Protein Design), healthomics-agentic-setup |
| `genomics-protein-design` | Directed evolution: sequence optimization, fitness scoring, EvoProt workflows | Agent 08 (Protein Design) |

### Category 3: Drug Discovery & Research

| Skill | What it teaches | Source agents |
|-------|----------------|--------------|
| `drug-target-identification` | Identify and validate drug targets: pathway analysis, protein interactions, tissue expression | Agents 05, 06, Kiro target-id agents |
| `drug-compound-optimization` | DMTA cycles: design, synthesis planning, assay analysis, lead optimization | Agent 25 (DMTA Orchestration) |
| `drug-safety-signal-detection` | Pharmacovigilance: FAERS analysis, PRR calculation, signal evaluation | Agent 22 (Safety Signal), Kiro cardioprotection |
| `drug-label-analysis` | FDA drug label analysis: indication extraction, comparison, automated reasoning guardrails | Agent 31 (Drug Label AR) |
| `drug-protein-search` | Protein data retrieval: UniProt queries, sequence analysis, functional annotation | Agent 19 (UniProt) |

### Category 4: Clinical Trials & Operations

| Skill | What it teaches | Source agents |
|-------|----------------|--------------|
| `clinical-trial-search` | Search ClinicalTrials.gov: filtering, visualization, drug info retrieval | Agent 15 (Clinical Study Research) |
| `clinical-protocol-generation` | Generate trial protocols: eligibility, endpoints, sample size, CDM best practices | Agent 16 (Protocol Generator) |
| `clinical-enrollment-monitoring` | Monitor enrollment: Veeva CTMS analysis, site performance, intervention recommendations | Agent 27 (Enrollment Pulse) |
| `clinical-patient-matching` | Match patients to trials: eligibility criteria, genomic markers, contraindications | Multi-agent: genomics + trials |
| `clinical-prior-authorization` | Automate prior auth: FHIR data analysis, billing guide matching, approval decisions | Agent 29 (Prior Auth) |

### Category 5: Biomarker Discovery & Oncology

| Skill | What it teaches | Source agents |
|-------|----------------|--------------|
| `biomarker-database-analysis` | Query biomarker databases: text-to-SQL, Redshift analytics, radiogenomics | Agent 01 (Biomarker DB Analyst) |
| `biomarker-multi-agent-discovery` | Orchestrate multi-modal biomarker discovery: clinical + genomic + imaging + literature | Multi-agent cancer biomarker workflow |
| `biomarker-pathway-analysis` | Biological pathway queries: Reactome graph, enrichment analysis, text-to-Cypher | Agents 05, 06 (Pathway/Enrichment) |
| `biomarker-literature-evidence` | Systematic literature review: PubMed search, evidence synthesis, citations | Agent 02 (Clinical Evidence), Agent 24 (Deep Research) |

### Category 6: Medical Standards & Terminology

| Skill | What it teaches | Source agents |
|-------|----------------|--------------|
| `terminology-ontology-lookup` | Standardize medical terms: EBI OLS, 200+ ontologies, entity extraction | Agent 35 (Terminology) |
| `terminology-data-harmonization` | Harmonize pharma data: ontology mapping, pipeline standardization | Agent 23 (Data Harmonisation) |
| `terminology-lab-data-standardization` | Convert instrument data to Allotrope/ASM: parsing, validation, export | Agent 36 (C4LS), life-sciences/instrument-data-to-allotrope |

### Category 7: Clinical Documentation & NLP

| Skill | What it teaches | Source agents |
|-------|----------------|--------------|
| `clinical-medical-nlp` | Medical NER, de-identification, summarization on clinical text | Agent 12 (JSL Medical Reports) |
| `clinical-radiology-validation` | Validate radiology reports against ACR guidelines | Agent 09 (Radiology Report) |
| `clinical-handwritten-extraction` | Extract structured data from handwritten medical forms | Agent 32 (IDP Handwritten) |
| `clinical-previsit-questionnaire` | Structured patient interview: conversational form-filling, PDF output | Agent 30 (Pre-Visit Questionnaire) |

### Category 8: Research & Literature

| Skill | What it teaches | Source agents |
|-------|----------------|--------------|
| `research-deep-literature-review` | Multi-step deep research: planning, iterative search, synthesis, citations | Agent 24 (Deep Research) |
| `research-biomedical-databases` | Query 30+ biomedical databases via Biomni: integrated multi-source research | Agent 28 (Research/Biomni) |
| `research-patent-analysis` | USPTO patent search: keyword, assignee, classification queries | Agent 14 (USPTO), Kiro unified-research |

### Category 9: Lab Automation & Operations

| Skill | What it teaches | Source agents |
|-------|----------------|--------------|
| `lab-sila2-automation` | Control SiLA2 lab devices: HPLC monitoring, anomaly detection, autonomous control | Agent 34 (SiLA2 Lab) |
| `lab-invivo-scheduling` | Optimize in-vivo study schedules: constraint programming, resource balancing | Agent 21 (In Vivo Scheduler) |
| `lab-device-monitoring` | Medical device monitoring: alerts, literature search, trial matching | Agent 26 (Medical Device) |

### Category 10: Multi-Agent Orchestration

| Skill | What it teaches | Source agents |
|-------|----------------|--------------|
| `orchestration-registry-discovery` | Dynamic agent discovery via AgentCore Registry: semantic search, connection, execution | AgentCore Registry samples |
| `orchestration-supervisor-pattern` | Build supervisor agents: agent-as-tools, routing, synthesis | Multi-agent cancer biomarker, Kiro medical-supervisor |
| `orchestration-competitive-intel` | Financial analysis workflow: SEC filings + web search + synthesis | Multi-agent competitive intelligence |

---

## MCP Servers Catalog

### agentcore-gateway/ (user deploys → gets MCP endpoint)

| Server | Tools | Source | Deployment |
|--------|-------|--------|------------|
| `biomni-research-tools` | 30+ biomedical database query tools | Agent 28 | CloudFormation → Lambda → Gateway |
| (future) `genomics-tools` | Variant annotation, VCF processing | Agent 17 (post-migration) | Same pattern |
| (future) `clinical-trials-tools` | Trial search, protocol helpers | Agents 15, 16 (post-migration) | Same pattern |

### agentcore-runtime/ (user deploys → MCP server on Runtime)

| Server | Tools | Source | Deployment |
|--------|-------|--------|------------|
| `ontology-lookup-service` | 7 ontology tools (search, lookup, map) across 200+ EBI ontologies | Agent 35 | Docker → AgentCore Runtime |
| (future) `lab-data-converter` | Instrument-to-Allotrope conversion | Agent 36 | Same pattern |

### aws-public/ (user configures — no deployment)

| Server | Transport | URL/Command | What it provides |
|--------|-----------|-------------|------------------|
| `aws-healthomics` | stdio (local) | `uvx awslabs.aws-healthomics-mcp-server@latest` | 60+ HealthOmics workflow/run/store tools |
| `aws-knowledge` | HTTP (remote) | `https://knowledge-mcp.global.api.aws` | AWS documentation search, architecture guidance |
| `agentcore-docs` | stdio (local) | `uvx awslabs.amazon-bedrock-agentcore-mcp-server@latest` | AgentCore documentation and API reference |
| `strands-docs` | stdio (local) | `uvx strands-agents-mcp-server` | Strands Agents SDK documentation |
| `aws-mcp` | stdio (local) | `uvx mcp-proxy-for-aws@latest https://aws-mcp.us-east-1.api.aws/mcp` | 300+ AWS service operations (from AWS Agent Toolkit) |

### third-party/ (user configures — no deployment)

| Server | Transport | URL | Provider |
|--------|-----------|-----|----------|
| `pubmed` | HTTP | `https://pubmed.mcp.claude.com/mcp` | U.S. National Library of Medicine |
| `open-targets` | HTTP | `https://mcp.platform.opentargets.org/mcp` | Open Targets |
| `chembl` | HTTP | `https://mcp.deepsense.ai/chembl/mcp` | deepsense.ai |
| `clinical-trials` | HTTP | `https://mcp.deepsense.ai/clinical_trials/mcp` | deepsense.ai |
| `biorxiv` | HTTP | `https://mcp.deepsense.ai/biorxiv/mcp` | deepsense.ai |
| `synapse` | HTTP | `https://mcp.synapse.org/mcp` | Sage Bionetworks |
| `biorender` | HTTP | `https://mcp.services.biorender.com/mcp` | BioRender |
| `consensus` | HTTP | `https://mcp.consensus.app/mcp` | Consensus |
| `cortellis` | HTTP | `https://api.clarivate.com/lifesciences/mcp-regulatory/mcp` | Clarivate |
| `adisinsight` | HTTP | `https://adisinsight-mcp.springer.com/mcp` | Springer Nature |
| `medidata` | HTTP | `https://mcp.imedidata.com/mcp` | Medidata Solutions |
| `wiley` | HTTP | `https://connector.scholargateway.ai/mcp` | Wiley |
| `owkin` | HTTP | `https://mcp.k.owkin.com/mcp` | Owkin |
| `10x-genomics` | MCPB (local) | Binary download | 10x Genomics |
| `tooluniverse` | MCPB (local) | Binary download | MIMS Harvard |

---

## Platform Adapters

### Claude Code (`platforms/claude-code/`)

```
platforms/claude-code/
├── .mcp.json                           ← Full MCP config (all servers)
└── .claude/
    └── skills/
        └── hcls/
            ├── SKILL.md                ← Master skill that references sub-skills
            └── (sub-skills loaded from skills/ on demand)
```

Installed via: `/plugin marketplace add aws-samples/amazon-bedrock-agents-healthcare-lifesciences` then `/plugin install hcls-agents`

### Kiro (`platforms/kiro/`)

```
platforms/kiro/
├── POWER.md                            ← Power definition
├── mcp.json                            ← MCP config (Kiro format)
└── steering/
    ├── product.md                      ← What the toolkit is
    ├── structure.md                    ← How it's organized
    ├── tech.md                         ← Technology stack
    └── domain-<category>.md            ← Per-domain steering (generated from skills/)
```

Installed via: local path reference in project `.kiro/` config

### Codex (`platforms/codex/`)

```
platforms/codex/
├── AGENTS.md                           ← Codex agent instructions
├── config.toml                         ← MCP config (TOML format)
└── skill/
    ├── SKILL.md                        ← Master skill
    └── references/                     ← Domain references
```

Installed via: `codex plugin marketplace add aws-samples/amazon-bedrock-agents-healthcare-lifesciences`

### Q Desktop (`platforms/q-desktop/`)

```
platforms/q-desktop/
├── README.md                           ← Setup instructions
├── skills/                             ← Skills formatted for ~/.quickwork/skills/
│   └── hcls-<domain>/SKILL.md
└── mcp-config.md                       ← Step-by-step MCP connection guide
```

Installed via: Copy skills to `~/.quickwork/skills/`, add MCP servers in Settings → Capabilities

### Interactive Setup (`platforms/setup.sh`)

Interactive installer following the HealthOmics agentic-setup pattern:
1. Asks which platform (Claude Code, Kiro, Codex, Q Desktop, Cursor)
2. Asks global vs. project-level install
3. Copies appropriate configs to the right locations
4. Configures MCP servers
5. Validates setup

---

## Marketplace Registration

### .claude-plugin/marketplace.json (repo root)

```json
{
  "name": "amazon-bedrock-agents-healthcare-lifesciences",
  "owner": { "name": "Amazon Web Services" },
  "metadata": {
    "version": "1.0.0",
    "description": "Healthcare and Life Sciences domain capabilities for AI coding assistants — skills, MCP tools, and production agent patterns for genomics, drug discovery, clinical trials, and more."
  },
  "plugins": [
    {
      "name": "hcls-agents",
      "source": "./plugins/hcls-agents",
      "description": "HCLS domain skills and MCP tools for building healthcare and life sciences agents on AWS",
      "category": "healthcare",
      "keywords": ["healthcare", "life-sciences", "genomics", "clinical", "drug-discovery", "bedrock", "agentcore"]
    }
  ]
}
```

### .agents/plugins/marketplace.json (Codex format)

```json
{
  "name": "amazon-bedrock-agents-healthcare-lifesciences",
  "interface": { "displayName": "HCLS Agents Toolkit" },
  "plugins": [
    {
      "name": "hcls-agents",
      "source": { "source": "local", "path": "./plugins/hcls-agents" },
      "policy": { "installation": "AVAILABLE" },
      "category": "Healthcare"
    }
  ]
}
```

---

## Validation

`tools/validate.py` (following AWS Agent Toolkit pattern) validates:
- Both marketplace manifests exist and have correct structure
- Plugin manifests (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`) are valid
- All SKILL.md files have valid YAML frontmatter (`name` in kebab-case, `description` present)
- MCP configs have valid `command`/`args` (stdio) or `url` (HTTP) fields
- Skill `scripts/` files are executable
- Platform adapter configs reference valid skills and servers

---

## Implementation Plan and Roadmap

This plan aligns with the phased roadmap in `repository-transformation-roadmap.md`. A separate parallel project handles the v1→v2 agent migration (CloudFormation/Lambda → AgentCore/Strands). This framework project does NOT block on that migration — it builds the skills/MCP/platform infrastructure that migrated agents will naturally integrate with.

### Phase 1: Framework Foundation (Weeks 1-2) — CURRENT

**Status:** Scaffold complete. Ready for community contribution.

| Deliverable | Status | Notes |
|------------|--------|-------|
| Directory structure (`skills/`, `mcp-servers/`, `plugins/`, `platforms/`) | Done | All folders created |
| Marketplace manifests (Claude Code + Codex) | Done | `.claude-plugin/` + `.agents/plugins/` |
| Plugin definition (`plugins/hcls-agents/`) | Done | Both manifest formats |
| MCP server configs — AWS public (5 servers) | Done | .mcp.json files |
| MCP server configs — third-party (15 servers) | Done | .mcp.json files |
| Platform adapters (Claude Code, Kiro, Codex, Q Desktop) | Done | Configs + READMEs |
| Interactive setup.sh | Done | Multi-platform installer |
| Builder skills (3): get-started, build-agent, deploy-agent | Done | SKILL.md with content |
| Validation script | Done | `tools/validate.py` |
| Rules file | Done | `rules/hcls-agent-rules.md` |
| Design documentation | Done | This document |

### Phase 2: Domain Skills + Platform Testing (Weeks 3-6)

**Goal:** Fill in domain skills content, test across platforms, demonstrate end-to-end workflows.

| Deliverable | Effort | Dependency |
|------------|--------|------------|
| Write remaining builder skills (hcls-add-mcp-tools, hcls-domain-conventions) | 2-3 days | None |
| Write genomics skills (variant-interpretation, single-cell-qc, healthomics-workflows) | 1 week | None — can reference existing agent 17, 20 code |
| Write drug discovery skills (target-id, safety-signal, compound-optimization) | 1 week | None — can reference agents 05, 22, 25 |
| Write clinical trials skills (trial-search, protocol-generation, enrollment) | 1 week | None — can reference agents 15, 16, 27 |
| Test plugin install in Claude Code | 2 days | Phase 1 complete |
| Test Kiro power configuration | 2 days | Phase 1 complete |
| Test Q Desktop skill loading + MCP server connections | 2 days | Phase 1 complete |
| Document end-to-end demo: researcher using Q Desktop + MCP servers | 3 days | MCP servers configured |
| Document end-to-end demo: developer using Claude Code + skills to build agent | 3 days | Skills written |

**Parallel migration dependency:** As agents complete v1→v2 migration, their domain knowledge should be captured in skills. Each migrated agent gets ~1 extra day of work to produce a SKILL.md + registry record.

### Phase 3: Deployable MCP Servers + Advanced Skills (Weeks 7-12)

**Goal:** Extract deployable MCP servers from catalog agents, write orchestration skills, complete platform parity.

| Deliverable | Effort | Dependency |
|------------|--------|------------|
| Extract Biomni Gateway deployment as standalone MCP server | 1 week | Agent 28 stable |
| Extract OLS Runtime deployment as standalone MCP server | 1 week | Agent 35 stable |
| Write biomarker skills (database-analysis, pathway-analysis, multi-agent) | 1 week | None |
| Write terminology skills (ontology-lookup, data-harmonization) | 3-4 days | None |
| Write research skills (deep-literature, biomedical-databases) | 3-4 days | None |
| Write orchestration skills (registry-discovery, supervisor-pattern) | 1 week | Registry samples available |
| Complete Kiro steering documents (generate from skills) | 3-4 days | Skills written |
| Skill format adapter tooling (build script generating per-platform output) | 3-4 days | All skills written |
| Full validation suite + CI integration | 2-3 days | All content in place |

### Phase 4: Registry Integration + Community (Months 4-6+)

**Goal:** Agents registered in AgentCore Registry, dynamic orchestration demonstrated, community contribution framework live.

| Deliverable | Effort | Dependency |
|------------|--------|------------|
| Create HCLS AgentCore Registry | 2-3 weeks | v2 agents deployed |
| Register v2 agents (as they complete migration) | Ongoing | Migration project |
| Build HCLS orchestrator agent (dynamic discovery) | 3-4 weeks | Registry populated |
| Demonstrate multi-agent workflows via Registry | 2 weeks | Orchestrator working |
| Community contribution templates + guidelines | 1-2 weeks | Framework stable |
| Enterprise distribution readiness | 2-3 weeks | Platform support mature |

### Alignment with Original Roadmap

| Original roadmap phase | This implementation plan | Delta |
|------------------------|-------------------------|-------|
| Short term (4-6 weeks): Package what exists | Phases 1-2: Framework + domain skills | Aligned — we front-loaded the scaffold |
| Medium term (2-3 months): Domain skills + platform demos | Phases 2-3: Domain skills + MCP extraction + testing | Aligned — platform demos in Phase 2, MCP extraction in Phase 3 |
| Long term (6+ months): Composable platform | Phase 4: Registry + orchestration + community | Aligned — depends on migration progress |

### Coordination with v1→v2 Migration Project

The migration project converts legacy CloudFormation/Lambda agents to AgentCore/Strands. This framework project and that migration project are complementary:

```
Migration delivers → v2 agent with Strands tools + AgentCore deployment
This project adds  → SKILL.md + Registry record + MCP documentation
Combined result    → agent is deployable, discoverable, composable, and documented
```

**Per-agent handoff (adds ~1 day to migration):**
1. Migration owner converts agent to Strands
2. Migration owner also writes `skills/<domain>/SKILL.md` (they understand the domain deeply at that moment)
3. Migration owner adds `registry/record.json` to the agent folder
4. This project integrates the skill into the plugin and validates across platforms

**Neither project blocks the other in the short term.** Skills can be written against existing agent code (even v1). The migration just makes agents natively expose MCP endpoints.

### Consumer Platforms

All platforms listed below consume the same skills and MCP servers — the framework packages them appropriately for each:

| Platform | Type | Skills | MCP Servers | Status |
|----------|------|--------|-------------|--------|
| **Claude Code** | AI coding assistant | Via plugin install | Via .mcp.json | Phase 1 ready |
| **Kiro** | AI coding assistant | Via POWER.md + steering/ | Via mcp.json | Phase 1 ready |
| **Codex** | AI coding assistant | Via .codex-plugin | Via config.toml | Phase 1 ready |
| **Amazon Q Desktop** | End-user platform | Via ~/.quickwork/skills/ | Via Settings → Capabilities | Phase 1 ready |
| **Claude Co-work** | End-user platform | Via skill loading | Via app UI | Phase 2 (testing) |
| **Cursor / VS Code** | IDE extension | Via .cursor/skills/ | Via .cursor/mcp.json | Phase 1 ready (uses Claude Code config) |
| **Production Agents** | AgentCore Runtime | Via Strands AgentSkills | Via Gateway/Runtime | Phase 3-4 |
| **AgentCore Registry** | Discovery service | As AGENT_SKILLS records | As MCP records | Phase 4 |

**Amazon Q Desktop** is a key consumer platform: non-technical researchers and clinicians connect Q Desktop to deployed HCLS MCP servers (Biomni Gateway, OLS) and load domain skills — executing genomics, drug discovery, and clinical workflows through natural language without deploying any agents themselves.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Skills at top level (`skills/`), not nested under plugin | Skills are the source of truth consumed by all layers — plugin, platforms, agents, registry |
| MCP servers organized by deployment model | Clear user mental model: "do I deploy this or just configure it?" |
| Platform adapters separate from plugin | Plugin is the marketplace definition; adapters are per-tool installation mechanics |
| No symlinks in plugin to skills/ | Git submodule/symlink issues across platforms. Plugin references skills by path. |
| Existing agents_catalog/ unchanged | No disruption to current workflows; skills layer on top |
| Follow Anthropic life-sciences marketplace format | Proven pattern, directly installable, consistent with ecosystem |
| Follow HealthOmics setup.sh pattern | Proven UX for multi-platform configuration |
| Follow AWS Agent Toolkit dual-manifest pattern | Claude Code + Codex covered from day one |
