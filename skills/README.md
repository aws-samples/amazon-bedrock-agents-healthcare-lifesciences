# Skills

Skills are portable domain knowledge that teach AI coding assistants and end-user platforms how to accomplish HCLS workflows. Each skill contains instructions, executable scripts, and reference documentation.

## Structure

```
skills/<skill-name>/
├── SKILL.md          ← Instructions (YAML frontmatter + markdown body)
├── scripts/          ← Executable code the AI assistant runs (Python, bash)
└── references/       ← Domain documentation loaded on-demand for context
```

## Skill Categories

### Builder Skills (how to build HCLS agents)

| Skill | What it teaches |
|-------|----------------|
| [hcls-get-started](hcls-get-started/) | Orient in this toolkit, choose a pattern, first steps |
| [hcls-build-agent](hcls-build-agent/) | Structure tools, prompts, and domain knowledge for an HCLS agent |
| [hcls-deploy-agent](hcls-deploy-agent/) | Deploy to AgentCore: Gateway, Runtime, Memory, Identity |
| [hcls-add-mcp-tools](hcls-add-mcp-tools/) | Add MCP tools via Gateway targets or Runtime servers |
| [hcls-domain-conventions](hcls-domain-conventions/) | HCLS data formats, ontologies, PHI handling, compliance |

### Genomics & Variant Analysis

| Skill | What it teaches |
|-------|----------------|
| [genomics-variant-interpretation](genomics-variant-interpretation/) | VCF interpretation, pathogenicity classification, clinical reporting |
| [genomics-single-cell-qc](genomics-single-cell-qc/) | Single-cell RNA-seq quality control and metrics analysis |
| [genomics-healthomics-workflows](genomics-healthomics-workflows/) | Run WDL/Nextflow workflows on AWS HealthOmics |

### Drug Discovery & Research

| Skill | What it teaches |
|-------|----------------|
| [drug-target-identification](drug-target-identification/) | Target validation: pathway analysis, protein interactions, tissue expression |
| [drug-compound-optimization](drug-compound-optimization/) | DMTA cycles, lead optimization, molecular design |
| [drug-safety-signal-detection](drug-safety-signal-detection/) | Pharmacovigilance, FAERS analysis, PRR calculation |
| [drug-label-analysis](drug-label-analysis/) | FDA drug label analysis and automated reasoning |

### Clinical Trials & Operations

| Skill | What it teaches |
|-------|----------------|
| [clinical-trial-search](clinical-trial-search/) | Search and filter ClinicalTrials.gov data |
| [clinical-protocol-generation](clinical-protocol-generation/) | Generate trial protocols with eligibility, endpoints, sample size |
| [clinical-enrollment-monitoring](clinical-enrollment-monitoring/) | Enrollment analytics and site performance insights |

### Biomarker Discovery & Oncology

| Skill | What it teaches |
|-------|----------------|
| [biomarker-database-analysis](biomarker-database-analysis/) | Query biomarker databases, text-to-SQL analytics |
| [biomarker-multi-agent-discovery](biomarker-multi-agent-discovery/) | Multi-modal biomarker discovery orchestration |
| [biomarker-pathway-analysis](biomarker-pathway-analysis/) | Biological pathway queries, enrichment analysis |

### Medical Standards & Terminology

| Skill | What it teaches |
|-------|----------------|
| [terminology-ontology-lookup](terminology-ontology-lookup/) | Standardize terms against 200+ EBI ontologies |
| [terminology-data-harmonization](terminology-data-harmonization/) | Harmonize pharma pipeline data using ontologies |

### Research & Literature

| Skill | What it teaches |
|-------|----------------|
| [research-deep-literature-review](research-deep-literature-review/) | Multi-step deep research with iterative literature search |
| [research-biomedical-databases](research-biomedical-databases/) | Query 30+ biomedical databases via Biomni tools |

### Multi-Agent Orchestration

| Skill | What it teaches |
|-------|----------------|
| [orchestration-registry-discovery](orchestration-registry-discovery/) | Dynamic agent discovery via AgentCore Registry |
| [orchestration-supervisor-pattern](orchestration-supervisor-pattern/) | Build supervisor agents with agents-as-tools |

## How Skills Work

1. AI assistant loads the SKILL.md into context (triggered by user request matching the skill's description)
2. SKILL.md provides step-by-step workflow instructions
3. When execution is needed, the assistant runs scripts from `scripts/`
4. When domain context is needed, the assistant reads files from `references/`
5. When AWS infrastructure actions are needed, the skill directs the assistant to use the appropriate AWS MCP server (HealthOmics, Athena, aws-mcp, etc.)

## Using Skills Across Platforms

| Platform | How skills are consumed |
|----------|----------------------|
| Claude Code | Loaded via plugin install, referenced in context |
| Kiro | Adapted to POWER.md + steering/ format |
| Codex | Loaded via .codex-plugin skills path |
| Q Desktop | Copied to ~/.quickwork/skills/ |
| Production agents | Loaded via Strands AgentSkills at runtime |
| AgentCore Registry | Registered as AGENT_SKILLS records for dynamic discovery |
