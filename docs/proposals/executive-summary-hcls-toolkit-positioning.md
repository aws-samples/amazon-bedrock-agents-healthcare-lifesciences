# HCLS Agents Toolkit: Strategic Positioning

> The HCLS Agents Toolkit becomes a library of healthcare domain capabilities — deployable as production agents, consumable as developer skills, and connectable as MCP tools — serving builders in their IDEs, researchers in Q Desktop, and clinicians through production applications.

## Executive Summary

The HCLS Agents Toolkit is a library of healthcare and life sciences domain capabilities — deployable agents, reusable skills, and MCP-based tools — that enables builders and end-users to execute HCLS workflows on AWS. This document describes how the toolkit complements and integrates with the broader ecosystem of AI development tools and consumption surfaces.

---

## Why Now: 
The common ask: **domain-specific AI capabilities that non-technical users can access through natural language, without deploying infrastructure themselves.**

The HCLS Agents Toolkit already has the domain capabilities (36+ agents). What's missing is the portable interface layer that makes them accessible to these consumption surfaces.

---

## The Ecosystem

Four distinct offerings serve different audiences at different stages:

| Offering | What it provides | Who it serves |
|----------|-----------------|---------------|
| **AWS Agent Toolkit** | Generic AWS best practices — build, deploy, debug, harden agents on AWS | Any developer building agents on AWS |
| **HCLS Agents Toolkit** (this repo) | Domain-specific capabilities — HCLS workflows, tools, knowledge, and production-ready agents | Builders and end-users in healthcare and life sciences |
| **AI Coding Assistants** (Claude Code, Kiro, Codex) | Developer IDE experience — code generation, deployment, debugging | Developers building software |
| **End-User Platforms** (Amazon Q Desktop, Claude Co-work) | Natural language interface for non-technical users to execute workflows | Researchers, clinicians, scientists |

---

## How They Compose

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   END-USER PLATFORMS (Amazon Q Desktop, Claude Co-work)                 │
│   Non-technical users execute HCLS workflows in natural language        │
│                                                                         │
│   Connects to:                                                          │
│   • HCLS MCP tools (via AgentCore Gateway/Runtime)                      │
│   • HCLS Skills (SKILL.md loaded as capabilities)                       │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   AI CODING ASSISTANTS (Claude Code, Kiro, Codex)                       │
│   Developers build, customize, and deploy HCLS agents                   │
│                                                                         │
│   Uses:                                                                 │
│   • AWS Agent Toolkit  → HOW to build agents on AWS                     │
│   • HCLS Toolkit Plugin → WHAT to build for healthcare/life sciences    │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   PRODUCTION RUNTIME (Amazon Bedrock AgentCore)                         │
│   Deployed agents serve end-users at scale with guardrails              │
│                                                                         │
│   • Agent Catalog → assembled, production-hardened agents               │
│   • AgentCore Gateway → HCLS tools exposed as hosted MCP endpoints      │
│   • AgentCore Runtime → MCP servers or full agent runtimes              │
│   • FAST template → full-stack deployment (React + Cognito + CDK)       │
│   • AgentCore Registry → dynamic discovery for multi-agent workflows    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Positioning by Offering

### 1. AWS Agent Toolkit (generic AWS)

**Relationship:** Complementary. The AWS Agent Toolkit teaches coding assistants HOW to build and deploy agents on AWS infrastructure. The HCLS Toolkit teaches them WHAT to build for healthcare and life sciences.

**Integration point:** A developer installs both plugins. The AWS Agent Toolkit handles scaffolding, IAM, deployment, debugging. The HCLS Toolkit provides domain knowledge, tool schemas, workflow patterns, and reference agents.

| AWS Agent Toolkit Skills | HCLS Toolkit Equivalent |
|--------------------------|-------------------------|
| `agents-get-started` — scaffold an agent | `hcls-get-started` — scaffold an HCLS agent using catalog patterns |
| `agents-deploy` — deploy to AgentCore | HCLS agents deploy using the same mechanism |
| `agents-harden` — guardrails, policies | HCLS adds HIPAA-aware guardrails, PHI handling |
| `agents-optimize` — evals, cost | HCLS adds domain-specific evaluation (clinical accuracy, scientific rigor) |

### 2. AI Coding Assistants (Claude Code, Kiro, Codex)

**Relationship:** The HCLS Toolkit exposes itself as an installable plugin for coding assistants.

**What developers get:**
- Skills that guide building HCLS agents (genomics, clinical trials, biomarker discovery, drug research)
- MCP server configs pointing to domain documentation and APIs
- Reference to catalog agents as templates and patterns
- Domain-specific conventions (data formats, ontologies, compliance requirements)

**Multi-assistant support:**
| Assistant | Format | What they consume |
|-----------|--------|-------------------|
| Claude Code | `.claude-plugin/` + SKILL.md | Skills + MCP servers |
| Kiro | `powers/` + `POWER.md` + `steering/` | Power with steering files + MCP servers |
| Codex | `.codex-plugin/` + SKILL.md | Skills + MCP servers |
| Cursor/VS Code/Windsurf | `.mcp.json` | MCP servers directly |

### 3. End-User Platforms (Amazon Q Desktop, Claude Co-work)

**Relationship:** The HCLS Toolkit provides domain tools and skills that non-technical users access directly — without deploying a full agent.

**What end-users get:**
- Connect to deployed HCLS MCP servers (AgentCore Gateway/Runtime) for domain tools
- Load HCLS skills as workflow guidance
- Execute clinical, genomics, and research workflows in natural language

**Example flows:**
- A researcher connects to the Biomni Gateway (agent 28) → queries 30+ biomedical databases via natural language
- A clinician connects to the OLS MCP server (agent 35) → standardizes medical terminology against 200+ ontologies
- A scientist loads the C4LS skills (agent 36) → converts instrument data to standardized formats

**Key distinction:** End-user platforms consume the SAME MCP tools and skills that developers use — but without the IDE context. The deployed AgentCore Gateway/Runtime acts as the bridge.

### 4. HCLS Agents Toolkit (this repo — the unique offering)

**What is unique to this toolkit:**
- A catalog of 36+ production-ready HCLS agents spanning drug research, clinical trials, genomics, and commercialization
- Domain-specific MCP tools (ontology lookup, variant interpretation, biomarker databases, clinical trial matching, drug label analysis)
- HCLS workflow knowledge encoded as portable skills
- Multi-agent collaboration patterns for complex HCLS workflows (cancer biomarker discovery, clinical trial protocols)
- HCLS-specific guardrails (HIPAA compliance, PHI handling, clinical validation)
- Evaluation frameworks for clinical accuracy and scientific rigor

**The catalog remains the core product.** Skills and MCP servers are the portable interface layer that makes catalog capabilities consumable across all surfaces.

---

## Multi-Agent Orchestration via AgentCore Registry

A key differentiator: catalog agents don't just run in isolation — they compose into workflows dynamically.

**AgentCore Registry** provides:
- A centralized catalog where deployed agents, MCP servers, and skills register themselves with rich descriptions
- **Semantic search** — an orchestrator finds relevant capabilities using natural language (e.g., "variant interpretation" matches the genomics agent even if those exact words aren't in its name)
- **Dynamic discovery at runtime** — no hardcoded integrations; the orchestrator builds its toolset per-request
- **Mixed protocol support** — MCP servers (via Gateway) and A2A agents (via Runtime) discovered from a single search
- **Approval workflow** — admin-controlled publishing ensures only validated agents are discoverable

**What this enables for HCLS:**

A dynamic orchestrator agent receives "Analyze this patient's genomic data and find matching clinical trials" and at runtime:
1. Searches the Registry → discovers the variant interpreter agent + the clinical trial matching agent
2. Connects to both (MCP + A2A)
3. Executes the multi-step workflow without any hardcoded integration

**New HCLS agents become instantly available to workflows** — register in the Registry, get discovered automatically. No redeployment of the orchestrator.

This transforms the catalog from "pick one agent" to "agents are composable services assembled on demand."

---

## Security and Compliance Position

This toolkit is currently positioned as **demonstrative/non-clinical** — not intended for production use with PHI without appropriate compliance review.

**Current state:**
- MIT-0 license with explicit disclaimer: not for clinical use, not a substitute for professional medical advice
- Each customer is responsible for determining HIPAA applicability and entering an AWS BAA

**For the portable interface layer (skills + MCP):**
- Skills contain workflow knowledge, not patient data — no PHI flows through SKILL.md files
- MCP tools connect to data sources at runtime — PHI handling depends on the backend, not the skill/MCP layer
- AgentCore Gateway/Runtime provides authentication (Cognito OAuth2, IAM SigV4) and access control
- Cedar policies can enforce data access guardrails at the tool level

**Action required:** Formal security review of the MCP tool layer before any customer-facing deployment involving PHI. This is acknowledged as a gap to be addressed in medium-term implementation.

---

## Value Proposition by Persona

| Persona | Current experience | With integrated toolkit |
|---------|-------------------|------------------------|
| **HCLS Developer** (building agents) | Clone repo, read READMEs, manually copy templates | Install HCLS + AWS plugins → guided scaffolding, domain knowledge, automated deployment |
| **Researcher** (exploring data) | Must deploy a full agent to get domain tools | Connect Q Desktop/Co-work to HCLS MCP servers → immediate domain tool access |
| **Clinician** (executing workflows) | No direct access — needs deployed agent + UI | Connect to AgentCore Gateway → natural language clinical workflows |
| **Platform team** (building internal tools) | Integrate agents one-by-one | Compose catalog agents + shared MCP tools → modular HCLS platform |

---

## Answering the Market Question

> "Are you building industry-specific modules for Amazon Q Desktop? Can you give us visibility on the roadmap?"

**Answer:** The HCLS Agents Toolkit provides healthcare and life sciences capabilities as portable skills and MCP tools deployable to AgentCore. These are consumable by any MCP-compatible surface — including Amazon Q Desktop, Claude Co-work, coding assistants, and custom applications. The toolkit includes a catalog of 36+ production-ready agents alongside the domain tools and skills that power them. Builders can deploy complete agents for production use, or connect end-user platforms directly to HCLS domain tools for exploratory and operational workflows.

---

## Summary

The HCLS Agents Toolkit is positioned as the **domain layer** in a composable stack:

- **AWS Agent Toolkit** = infrastructure best practices (how to build on AWS)
- **HCLS Agents Toolkit** = domain capabilities (what to build for healthcare/life sciences)
- **Coding Assistants** = developer experience (who builds it)
- **End-User Platforms** = consumption experience (who uses it)

Each layer is independently valuable. Together, they enable a complete path from exploration to production for HCLS AI workflows on AWS.
