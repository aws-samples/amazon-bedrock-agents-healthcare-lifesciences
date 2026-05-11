# HCLS Agents Toolkit: Repository Transformation Roadmap

## Context

This document proposes changes to transform the HCLS Agents Toolkit repository from a collection of standalone agents into a composable platform where domain capabilities are expressed as portable skills, MCP tools, and production-ready agents. These changes complement the ongoing parallel effort to migrate legacy Bedrock agents (v1 CloudFormation/Lambda pattern) to AgentCore with the Strands framework.

---

## Current State

### What exists today

| Component | State | Pattern |
|-----------|-------|---------|
| 36+ catalog agents | Mixed — some v1 (CloudFormation/Lambda), some v2 (AgentCore/Strands) | Self-contained, independently deployable |
| `agentcore_template/` | Production-ready | Backend-only AgentCore stack (Runtime, Gateway, Identity, Memory, Observability) + Streamlit UI |
| [FAST template](https://github.com/awslabs/fullstack-solution-template-for-agentcore) | External, production-ready | Full-stack: React frontend (Amplify) + Cognito auth + AgentCore backend + CDK/Terraform deployment |
| Agent 28 (Research/Biomni) | Production-ready | AgentCore Gateway as MCP endpoint with 30+ database tools |
| Agent 35 (Terminology/OLS) | Production-ready | Built on FAST template + custom OLS MCP server on AgentCore Runtime |
| Agent 36 (C4LS) | Production-ready | Strands `AgentSkills` (SKILL.md) + external MCP connectors |
| Kiro Power | Functional | `powers/hcls-agentcore-builder/` with steering files + MCP configs |
| Multi-agent collaboration | Functional | Cancer biomarker discovery, clinical trials, competitive intel |

### Two deployment templates available

| Template | Scope | Use when |
|----------|-------|----------|
| **`agentcore_template/`** (this repo) | Backend-only: AgentCore Runtime + Gateway + Memory + Streamlit dev UI | Rapid prototyping, backend development, or BYO frontend |
| **[FAST](https://github.com/awslabs/fullstack-solution-template-for-agentcore)** (external) | Full-stack: React/Amplify frontend + Cognito + AgentCore backend + CDK | Production deployments needing a complete, secured web application |

Agent 35 (Terminology) demonstrates the FAST pattern: fork FAST, add domain-specific tools (OLS MCP server), customize the agent and frontend — production-ready full-stack deployment with minimal effort. This is the recommended approach for production catalog agents going forward.

### Ongoing parallel work

The v1-to-v2 migration project is converting legacy CloudFormation/Lambda agents to AgentCore/Strands. This roadmap does NOT block on that migration — it builds the plugin/skills/MCP infrastructure that migrated agents will naturally fit into once converted.

---

## Architectural Principles

1. **MCP servers are the universal tool primitive** — deploy once to AgentCore, consumable by any MCP client (IDE, Co-work, Q Desktop, other agents)
2. **Skills are portable knowledge** — SKILL.md content is the source of truth, packaged per-surface with thin adapters
3. **Catalog agents are assembled products** — compose skills + MCP tools + guardrails + system prompt into production runtimes
4. **No duplication** — tools live in one place (MCP server); skills live in one place (SKILL.md); agents reference both
5. **Registry-driven composition** — deployed agents register in AgentCore Registry and become dynamically discoverable for multi-agent workflows

---

## Short Term (4-6 weeks): Package What Exists

**Goal:** Make the repo installable as a plugin and demonstrate the integration story. No new MCP servers or major refactoring.

### Deliverables

#### 1. Plugin marketplace manifest

Create `.claude-plugin/marketplace.json` registering this repo as an installable plugin source.

```
.claude-plugin/
  marketplace.json
```

#### 2. HCLS plugin skeleton

```
plugins/
  hcls-agents/
    .claude-plugin/plugin.json    ← Claude Code
    .codex-plugin/plugin.json     ← Codex
    .mcp.json                     ← MCP clients (Cursor, VS Code, etc.)
    README.md
    skills/
      hcls-get-started/SKILL.md
      hcls-build-agent/SKILL.md
      hcls-deploy-agent/SKILL.md
```

#### 3. Initial skills (3-4, extracted from existing content)

| Skill | Source material | What it teaches |
|-------|-----------------|-----------------|
| `hcls-get-started` | Kiro Power `POWER.md` + steering files | How to start building an HCLS agent using this repo |
| `hcls-build-agent` | `agentcore_template/` README + agent patterns | How to structure tools, prompts, and workflows for HCLS |
| `hcls-deploy-agent` | Deployment scripts, OLS deployment guide | How to deploy MCP servers and agents to AgentCore |
| `hcls-domain-conventions` | Extracted from agent READMEs | HCLS data formats, ontologies, compliance, PHI handling |

#### 4. MCP configuration pointing to existing servers

The `.mcp.json` references already-deployed or available MCP servers:

```json
{
  "mcpServers": {
    "awsknowledge": {
      "type": "http",
      "url": "https://knowledge-mcp.global.api.aws"
    },
    "agentcore-docs": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"]
    },
    "strands-docs": {
      "command": "uvx",
      "args": ["strands-agents-mcp-server"]
    },
    "healthomics": {
      "command": "uvx",
      "args": ["awslabs.aws-healthomics-mcp-server@latest"]
    }
  }
}
```

#### 5. Integration guide

A README documenting:
- How to install the HCLS plugin in Claude Code (`/plugin marketplace add ...`)
- How to configure MCP servers in Co-work and Q Desktop
- How the HCLS plugin complements the AWS Agent Toolkit
- Which catalog agents are directly accessible as MCP endpoints

#### 6. Maintain Kiro Power in parallel

Keep `powers/hcls-agentcore-builder/` as-is — update its content to stay in sync with the new skills.

### Effort estimate

| Task | Estimate |
|------|----------|
| Plugin manifests + structure | 1 day |
| Extract 3-4 skills from existing content | 1 week |
| MCP config + integration guide | 2-3 days |
| Testing across Claude Code + Kiro | 2-3 days |
| **Total** | **~2 weeks** |

### Dependencies on parallel migration

None. This phase uses existing content and deployed infrastructure.

---

## Medium Term (2-3 months): Domain Skills + MCP Tools

**Goal:** Build HCLS-specific skills with real workflow guidance and demonstrate end-user platform consumption (Q Desktop, Co-work connecting to deployed HCLS tools).

### Deliverables

#### 1. Domain-specific skills (5-8)

Skills that encode HCLS workflow knowledge, referencing catalog agents and MCP tools:

| Skill | Domain | What it enables |
|-------|--------|-----------------|
| `hcls-genomics-interpretation` | Genomics | Guide variant interpretation workflow (VCF → annotated → clinical report) |
| `hcls-clinical-trial-matching` | Clinical | Match patients to trials, generate protocols |
| `hcls-biomarker-discovery` | Research | Multi-agent biomarker discovery workflow |
| `hcls-drug-research` | Pharma | Protein design, DMTA cycles, drug label analysis |
| `hcls-medical-terminology` | Standards | Ontology standardization, CDISC mapping |
| `hcls-regulatory-compliance` | Compliance | HIPAA, PHI handling, clinical data guardrails |
| `hcls-lab-data-standardization` | Lab ops | Instrument data to Allotrope (extends C4LS pattern) |
| `hcls-safety-signal-detection` | Pharmacovigilance | Adverse event analysis, signal detection |

Each skill includes:
- Workflow steps
- Which MCP tools to use
- References to catalog agents as implementations
- Domain-specific guardrails and validation

#### 2. HCLS MCP server consolidation

Identify and document which catalog agents already expose MCP-accessible tools:

| Catalog Agent | MCP Endpoint | Tools available |
|---------------|-------------|-----------------|
| Agent 28 (Research/Biomni) | AgentCore Gateway | 30+ database query tools |
| Agent 35 (Terminology/OLS) | AgentCore Runtime | 7 ontology tools |
| Agent 36 (C4LS) | External (PubMed, OpenTargets) | Literature search, target lookup |

For agents completing v2 migration during this phase, ensure their Gateway tools are documented and connectable by end-user platforms.

#### 3. End-user platform demonstrations

Create documentation and demo configs showing:
- **Q Desktop:** Connect to deployed HCLS Gateway → execute research queries
- **Claude Co-work:** Load HCLS skills + connect MCP → run clinical workflows
- **Video/walkthrough:** Non-technical user performing HCLS workflow through natural language

#### 4. Skill format adapters

Create tooling or templates to generate surface-specific skill packaging from a single source:

```
skills/
  hcls-genomics-interpretation/
    SKILL.md                    ← source of truth
    references/                 ← domain docs
    scripts/                    ← executable helpers (optional)

build-skills.sh                 ← generates:
  → plugins/hcls-agents/skills/ (Claude Code format)
  → powers/ steering files      (Kiro format)
```

#### 5. Co-work / Q Desktop SKILL.md format

Ensure skills are compatible with both Co-work and Q Desktop's SKILL.md format (YAML frontmatter + markdown body with triggers/descriptions).

### Effort estimate

| Task | Estimate |
|------|----------|
| Write 5-8 domain skills | 3-4 weeks |
| MCP endpoint documentation + configs | 1 week |
| End-user platform demos | 2 weeks |
| Skill format adapter tooling | 1 week |
| Testing + iteration | 2 weeks |
| **Total** | **~2-3 months** |

### Dependencies on parallel migration

- Skills can reference v2 agents as they complete migration
- New MCP Gateway endpoints become available as agents are migrated
- Skills should be written to reference the target (v2) architecture, with notes on which agents are still in migration

---

## Long Term (6+ months): Composable HCLS Platform

**Goal:** Fully decomposed architecture where every catalog agent's capabilities are independently consumable as skills + MCP tools, registered in AgentCore Registry for dynamic discovery, and composable into multi-agent workflows by an orchestrator.

### Deliverables

#### 1. Every catalog agent decomposed and registered

As the v2 migration completes, each agent:
- **Deploys tools → AgentCore Gateway or Runtime** (MCP-accessible)
- **Publishes knowledge → SKILL.md** (portable across surfaces)
- **Registers in AgentCore Registry** (discoverable for orchestration)
- **Runs as assembled agent → AgentCore Runtime** (production deployment)

Example for the variant interpreter agent:

```
agents_catalog/17-variant-interpreter-agent/
├── skills/
│   └── variant-interpretation/SKILL.md     ← workflow knowledge
├── mcp-server/
│   └── (deployed to AgentCore Runtime)     ← genomics tools
├── agent/
│   └── main.py                             ← assembled agent (skills + tools + prompt)
├── registry/
│   └── record.json                         ← AgentCore Registry record (MCP + A2A descriptors)
└── README.md
```

On deployment, the agent automatically registers in the HCLS AgentCore Registry with:
- MCP server descriptor (tool schemas, transport config)
- A2A agent card (capabilities, skills, URL)
- Rich description for semantic search discoverability

#### 2. Dynamic multi-agent orchestration via AgentCore Registry

**This is the key architectural differentiator.** An HCLS orchestrator agent uses the AgentCore Registry to dynamically compose workflows:

```
User: "Analyze this patient's genomic data and find matching clinical trials"

Orchestrator Agent:
  1. SearchRegistryRecords("variant interpretation genomics")
     → discovers: variant-interpreter-agent (A2A) + genomics-store (MCP)
  2. SearchRegistryRecords("clinical trial matching eligibility")
     → discovers: clinical-trial-matching-agent (A2A)
  3. Connects to discovered agents dynamically
  4. Executes: interpret variants → extract findings → match to trials
  5. Returns: integrated report
```

**How it works (proven pattern from AgentCore samples):**
- Registry stores records with types: `MCP`, `A2A`, `AGENT_SKILLS`, `CUSTOM`
- `SearchRegistryRecords` API does semantic search over approved records
- Orchestrator parses descriptors to get connection metadata (MCP server schemas, A2A agent cards)
- Creates live connections: `MCPClient` for Gateway tools, `@tool` wrappers for A2A agents
- Executes using a Strands Agent built with only the dynamically discovered tools

**New agents become instantly available to workflows** — deploy, register, done. No orchestrator redeployment.

**HCLS-specific orchestration patterns:**

| Workflow | Agents composed | Trigger |
|----------|----------------|---------|
| Patient genomic analysis | Variant interpreter + Clinical trial matcher + Literature search | "Analyze VCF and recommend trials" |
| Biomarker discovery | Database analyst + Pathway analyst + Clinical evidence + Statistician | "Find CDx markers for NSCLC" |
| Drug research pipeline | Protein design + DMTA orchestrator + Safety signal detection | "Evaluate compound X" |
| Clinical documentation | Prior auth + PreVisit questionnaire + Medical terminology | "Prepare patient visit" |

#### 3. HCLS AgentCore Registry

A curated registry of all HCLS agents, MCP tools, and skills:

| Record | Type | Domain | What it exposes |
|--------|------|--------|-----------------|
| Biomni Research Gateway | MCP | Multi-database research | 30+ database query tools |
| OLS Terminology Server | MCP | Medical ontologies | 7 ontology tools |
| Genomics Variant Store | MCP | Genomics | HealthOmics queries, annotation |
| Variant Interpreter | A2A | Genomics | Clinical variant interpretation |
| Clinical Trial Matcher | A2A | Clinical | Trial eligibility, matching |
| Biomarker Discovery Suite | A2A | Research | Multi-agent biomarker workflow |
| Drug Label Analyzer | A2A | Regulatory | Label analysis, comparison |
| PubMed Connector | MCP | Literature | Search, fetch citations |
| OpenTargets | MCP | Target validation | Gene/disease lookup |
| Instrument-to-Allotrope | AGENT_SKILLS | Lab ops | Data standardization skill |

End-user platforms, coding assistants, and orchestrator agents all discover from the same registry.

#### 4. Multi-agent skill composition

Skills that orchestrate multiple MCP tools and reference multi-agent patterns:

```
hcls-cancer-biomarker-discovery/SKILL.md
  → Uses: biomni-gateway tools (databases)
  → Uses: genomics-store tools (variants)
  → Uses: pubmed tools (literature)
  → References: multi_agent_collaboration/cancer_biomarker_discovery/
  → Workflow: discovery → validation → clinical evidence
```

#### 5. Enterprise distribution readiness

Prepare for future admin-push capabilities (currently not available in Co-work or Q Desktop):
- Modular packaging: each HCLS domain is independently installable
- Configuration templates for org-wide MCP server connection
- Guardrail configs exportable as Cedar policies
- Documentation for platform teams integrating HCLS tools into custom applications

#### 6. Community contribution framework

Everyone building HCLS agents is solving similar domain problems — the community should benefit from shared skills, tools, and agents. Contributions are welcome immediately and don't need to wait for full platform maturity.

**What contributors can add:**

| Contribution type | What to submit | Template provided | Review process |
|-------------------|---------------|-------------------|----------------|
| **Skills** | SKILL.md + references/ + scripts/ (executable code the AI assistant runs) | `templates/skill/` | Domain expert review for accuracy |
| **Scripts** | Standalone Python tools (parsers, validators, converters) usable by skills or independently | `templates/script/` | Code review + test coverage |
| **MCP Servers** | MCP server deployable to AgentCore | `templates/mcp-server/` | Security review + deployment test |
| **Plugins** | Bundled skill + MCP config + manifest | `templates/plugin/` | Integration test across surfaces |
| **Agents** | Full AgentCore agent (existing pattern) | `agentcore_template/` | Architecture review + deployment test |

**Note on skills:** Skills are NOT just documentation. Following the [Anthropic Skills standard](https://github.com/anthropics/skills), a skill includes:
- `SKILL.md` — instructions that guide the AI assistant through a workflow
- `references/` — domain knowledge, schemas, runbooks the assistant reads for context
- `scripts/` — **executable code** (Python, bash) that the assistant runs to accomplish tasks (parsers, validators, converters, API clients, data transformers)

Example from the C4LS agent already in this repo (`agents_catalog/36-C4LS-example-agent/`):
```
skills/instrument-data-to-allotrope/
├── SKILL.md                          ← workflow instructions
├── scripts/
│   ├── convert_to_asm.py            ← executable: converts instrument data
│   ├── flatten_asm.py               ← executable: ASM → CSV
│   ├── export_parser.py             ← executable: generates standalone parser code
│   └── validate_asm.py              ← executable: validates output quality
└── references/
    ├── supported_instruments.md     ← domain knowledge
    ├── asm_schema_overview.md       ← schema reference
    └── field_classification_guide.md
```

See also: [Anthropic's mcp-builder skill](https://github.com/anthropics/skills/tree/main/skills/mcp-builder) as a reference for the scripts/ pattern.

**Contribution structure:**

```
contributions/
├── skills/                         ← Community-contributed skills
│   ├── <contributor>-<skill-name>/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   └── scripts/
├── mcp-servers/                    ← Community MCP server implementations
│   ├── <contributor>-<server-name>/
│   │   ├── server.py
│   │   ├── requirements.txt
│   │   └── README.md
├── scripts/                        ← Standalone utility scripts
│   ├── <contributor>-<script-name>/
│   │   ├── <script>.py
│   │   └── README.md
└── templates/                      ← Templates for each contribution type
    ├── skill/
    ├── script/
    ├── mcp-server/
    └── plugin/
```

**Contribution workflow:**

1. Contributor forks the repo
2. Creates their contribution using the appropriate template
3. Submits PR with:
   - Description of the HCLS use case it addresses
   - Which personas benefit (researcher, clinician, developer, etc.)
   - Test instructions or demo script
4. Review: domain expert validates accuracy, maintainer reviews code/security
5. Merge → automatically available in the plugin + optionally registered in the HCLS Registry

**Graduated promotion path:**

```
Community contribution (contributions/)
  → Validated and promoted to agents_catalog/ (if full agent)
  → Included in HCLS plugin skills/ (if skill)
  → Registered in HCLS AgentCore Registry (if deployable)
```

**What makes a good contribution:**
- Solves a real HCLS workflow problem (not generic)
- Includes a README explaining the use case and how to test
- For skills: validated by someone with domain expertise
- For MCP servers: deployable to AgentCore with provided scripts
- For agents: follows the `agentcore_template/` pattern

**Immediate call to action (post-exec approval):**

> The HCLS Agents Toolkit is now open for community contributions. If you're building skills, scripts, MCP tools, or agents for healthcare and life sciences workflows — contribute them here. Your work becomes instantly available to developers in their IDEs, researchers in Q Desktop, and production applications via AgentCore. Start with a skill (just a SKILL.md file) or a standalone script — no infrastructure required.

> We're specifically looking for contributions in: genomics/variant analysis, clinical trial workflows, drug discovery pipelines, regulatory/compliance automation, lab data standardization, medical terminology, and real-world evidence generation.

### Effort estimate

| Task | Estimate |
|------|----------|
| Decompose remaining catalog agents (as migration completes) | Ongoing, per-agent |
| Create HCLS AgentCore Registry + register existing v2 agents | 2-3 weeks |
| Build HCLS orchestrator agent (dynamic discovery pattern) | 3-4 weeks |
| Multi-agent skill composition | 4-6 weeks |
| Enterprise distribution templates | 2-3 weeks |
| Contribution framework | 2-3 weeks |
| **Total** | **6+ months (overlaps with migration)** |

### Dependencies on parallel migration

- **Critical dependency:** Long-term decomposition requires agents to be on v2 (AgentCore/Strands) to expose Gateway/Runtime MCP endpoints and register in the Registry
- The migration project delivers the agents; this roadmap delivers the plugin/skills/MCP/Registry layer on top
- Coordinate: as each agent completes migration, immediately create its skill + register in the HCLS Registry
- The orchestrator becomes more powerful with each agent registered — value compounds over time

---

## Coordination with v1 → v2 Migration

The v2 migration is an opportunity to build the portable interface layer simultaneously — rather than migrating first and adding skills/registry later as a second pass. The following recommendations help migration owners deliver both at once with minimal extra effort.

### Recommendations for Migration Project Owners

**When migrating each agent, additionally deliver these artifacts (medium-term requirements):**

#### 1. Extract a SKILL.md during migration

While converting the agent's logic to Strands, the migration owner already deeply understands the agent's workflow, domain knowledge, and tool interactions. Capture this as a SKILL.md at that moment — it costs 1-2 hours of extra work vs. having someone else reverse-engineer it later.

**Template for migration owners:**

```
skills/<workflow-name>/
├── SKILL.md              ← workflow instructions (template below)
├── scripts/              ← executable code the AI assistant can run
│   ├── validate.py       ← e.g., validate output format
│   ├── transform.py      ← e.g., data transformation
│   └── query.py          ← e.g., API query helper
└── references/           ← domain knowledge for context
    ├── data_formats.md   ← relevant schemas, ontologies
    └── examples.md       ← sample inputs/outputs
```

**SKILL.md template:**

```markdown
---
name: <agent-domain>-<workflow>
description: <one-line description of what this skill teaches an AI assistant to do>
---

# <Workflow Name>

## When to use this skill
<What user request triggers this workflow>

## Workflow steps
1. <Step — which tool or script to call and why>
2. ...

## Scripts
- `scripts/validate.py` — run to validate <what>
- `scripts/transform.py` — run to convert <input> to <output>

## Tools required (via MCP)
- <tool_name> — available via <MCP server / Gateway name>

## Domain knowledge
<Key domain context the AI assistant needs — data formats, ontologies, validation rules>
See references/ for detailed schemas and examples.

## References
- Agent implementation: agents_catalog/<agent-folder>/
- MCP endpoint: <Gateway/Runtime URL or SSM parameter>
```

#### 2. Expose tools via AgentCore Gateway (not just local Strands tools)

When moving Lambda action groups to Strands tools, also configure them as Gateway targets. This makes the tools accessible beyond the agent itself — to end-user platforms, coding assistants, and other agents.

**Concrete action:** For each tool function in the migrated agent, add a corresponding Gateway Lambda target in the `prerequisite/` infrastructure. Follow the pattern from agent 28 (Biomni Gateway).

#### 3. Create a Registry record JSON

Include a `registry/record.json` in the agent folder that can be used to register the agent post-deployment:

```json
{
  "name": "<agent-name>",
  "description": "<rich description for semantic search>",
  "descriptorType": "MCP",
  "descriptors": {
    "mcp": {
      "server": { "inlineContent": "<MCP server schema JSON>" },
      "tools": { "inlineContent": "<tool schemas JSON>" }
    }
  }
}
```

For agents that should also be invocable as A2A agents, include an `a2a` descriptor with the agent card.

#### 4. Follow the target folder structure

Migrated agents should land in this structure:

```
agents_catalog/<NN>-<agent-name>/
├── agent/                          ← Strands agent code (main.py, tools/, config/)
├── prerequisite/                   ← Infrastructure (Gateway, Lambda, Cognito)
├── skills/
│   └── <workflow>/
│       ├── SKILL.md                ← NEW: workflow instructions
│       ├── scripts/                ← NEW: executable code (parsers, validators, etc.)
│       └── references/             ← NEW: domain knowledge docs
├── registry/
│   └── record.json                 ← NEW: AgentCore Registry record
├── tests/                          ← Test scripts
└── README.md                       ← Updated with MCP endpoint info
```

**Two template options (both acceptable):**
- `agentcore_template/` → backend AgentCore stack + Streamlit UI. Good for agents where the focus is on tools/logic, or where a custom frontend exists.
- [FAST](https://github.com/awslabs/fullstack-solution-template-for-agentcore) → full-stack (React/Amplify + Cognito + CDK). Good when a complete, secured web application is needed. Agent 35 (Terminology) demonstrates this pattern.

Neither is required — contributors choose based on their deployment needs.

#### 5. Document the MCP endpoint in README

After migration, the README should include a "Connect to this agent's tools" section:

```markdown
## Connect via MCP

This agent's tools are accessible as an MCP endpoint via AgentCore Gateway.

**For Claude Code / Kiro / Cursor:**
Add to your `.mcp.json`:
\```json
{
  "hcls-<agent>": {
    "type": "http",
    "url": "<Gateway MCP URL from SSM parameter>"
  }
}
\```

**For Amazon Q Desktop / Claude Co-work:**
Settings → Capabilities → Add MCP → paste the URL above
```

### Migration checklist (per agent)

| Step | Standard migration | Additional for this roadmap | Extra effort |
|------|-------------------|---------------------------|--------------|
| Convert Lambda to Strands tools | ✅ | Also add as Gateway targets | +2-4 hours |
| Deploy to AgentCore Runtime | ✅ | Create registry/record.json | +1 hour |
| Write/update README | ✅ | Add MCP connection instructions | +30 min |
| Test agent works | ✅ | Test MCP endpoint independently | +1 hour |
| — | — | Extract SKILL.md | +1-2 hours |
| **Total extra per agent** | | | **~1 day** |

### Phased coordination

| Migration phase | This roadmap's action | Who |
|----------------|----------------------|-----|
| Agent migrated to Strands | Extract SKILL.md from agent's workflow knowledge | Migration owner |
| Agent tools moved to AgentCore Gateway | Document MCP endpoint, add to plugin `.mcp.json` | Migration owner + this project |
| Agent deployed to AgentCore Runtime | Register in HCLS AgentCore Registry | Automated via CI or migration owner |
| Agent validated in production | Reference from skills as "production-ready implementation" | This project |
| Agent registered in Registry | Automatically discoverable by orchestrator | Automatic |

**The two projects are complementary:** Migration provides the v2 agents with ~1 day of extra effort per agent to produce the skill, Registry record, and MCP documentation. This roadmap provides the infrastructure (plugin packaging, Registry setup, orchestrator) that consumes those artifacts. Neither blocks the other in the short term. Each migrated agent immediately gains discoverability and composability.

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| Short term | Plugin installable and functional in Claude Code + Kiro | Both tested, documented |
| Short term | Builder scaffolds + deploys an HCLS agent using skills (timed) | Under 30 min from clone to deployed agent |
| Short term | Internal builders actively using the plugin | 10+ within 6 weeks |
| Medium term | Non-technical user executes HCLS workflow via Q Desktop/Co-work | 3+ recorded demos with distinct personas |
| Medium term | Domain skills cover major HCLS verticals | 5-8 skills, each validated by domain expert |
| Medium term | Design partner feedback collected | 2-3 customers test and provide feedback |
| Long term | Catalog agents registered in HCLS AgentCore Registry | 100% of v2 agents |
| Long term | Orchestrator successfully composes multi-agent workflows | 4+ cross-agent workflows demonstrated |
| Long term | External contributions via skill/MCP/Registry framework | 5+ community contributions |
| Long term | Customer deployment using the toolkit | 1+ customer running HCLS tools in production |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Plugin formats diverge across surfaces | Skills need per-surface maintenance | Invest in shared source + adapter tooling (medium term) |
| No enterprise admin-push mechanism yet | Can't silently deploy to org users | Document manual setup; prepare for when platforms add this |
| v2 migration delays | Fewer agents have MCP endpoints | Short/medium term doesn't depend on migration; long term adjusts timeline |
| Skill quality/accuracy in clinical domain | Incorrect guidance in healthcare context | Domain expert review for all HCLS skills; disclaimers for non-clinical use |
| MCP server maintenance burden | Each deployed server needs upkeep | Consolidate related tools into fewer, larger Gateway deployments |

---

## Summary

| Phase | Theme | Key outcome |
|-------|-------|-------------|
| **Short term** (4-6 weeks) | Package what exists | Repo is an installable plugin; builders get guided skills |
| **Medium term** (2-3 months) | Domain skills + platform demos | Non-technical users access HCLS tools; 5-8 domain skills; design partner feedback |
| **Long term** (6+ months) | Composable platform + orchestration | Agents registered in Registry; dynamic multi-agent workflows; community contributions |

The transformation preserves the catalog as the core product while adding:
- A **portable interface layer** (skills + MCP) for accessibility across consumption surfaces
- A **registry and orchestration layer** (AgentCore Registry + dynamic discovery) for composable multi-agent workflows

Together, these enable the "research studio" and "Claude for Bioinformaticians" experiences customers are asking for — domain capabilities accessible to any persona, composable into any workflow, deployable to production with guardrails.
