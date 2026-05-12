# Decision Log: HCLS Agents Toolkit Transformation

## The Bigger "Why"

The market is shifting. Customers are asking: **"Are you building industry-specific modules for Amazon Q Desktop?"** and expecting AI-powered domain solutions that non-technical users can access without deploying infrastructure.

Simultaneously, the AI coding assistant landscape (Claude Code, Kiro, Codex, Cursor) is converging on a standard extensibility model: **skills (knowledge) + MCP servers (actions) + plugins (packaging)**. This model is now shared — with variations in format — across developer tools AND end-user platforms (Claude Co-work, Amazon Q Desktop).

The HCLS Agents Toolkit has a catalog of 36+ production-ready agents, but they're currently **only accessible as deployed runtimes**. A researcher can't use them without an AWS deployment. A developer can't discover them without reading READMEs. A clinician can't reach them without a custom UI.

**The transformation makes the same HCLS domain capabilities accessible across four consumption paths — without rebuilding anything from scratch.** The catalog agents remain the production product. We add a portable interface layer (skills + MCP tools) that makes those capabilities consumable by coding assistants and end-user platforms directly.

---

## Questions We Explored and Decisions Reached

### Q1: How does the Agent Catalog fit within a plugin-like toolkit setup?

**Options considered:**
- A) Catalog as "recipes" that skills know how to cook
- B) Catalog as composable building blocks for multi-agent workflows
- C) Catalog as the showcase, skills as the on-ramp
- D) Catalog agents become skill references (domain knowledge extracted from agent code)

**Decision:** A combination, but primarily **C (catalog is the product, skills are the on-ramp) with elements of D (skills extract domain knowledge from agents).**

**Why:** The catalog is the existing investment and the production offering. Skills don't replace agents — they make agents more discoverable and their domain knowledge more portable. An agent's system prompt, tool logic, and workflow patterns contain valuable domain knowledge that can be extracted as a skill for developer/user consumption.

---

### Q2: If I have skills and MCP servers, why do I need custom agents at all?

**Answer:** You need deployed agents when you need:
- Non-technical end-users (they won't use an IDE)
- Compliance/audit trails (HIPAA requires fixed guardrails, not a chat session)
- Scale (1000 concurrent users)
- Determinism (pinned model version, tested tool subset)
- Cost optimization (right-sized model per task)
- System integration (EHR, event-driven pipelines)

**Decision:** Skills + MCP servers serve exploration and development. Deployed catalog agents serve production. Same capabilities, different packaging for different contexts.

**Why:** A researcher exploring "what biomarkers exist for NSCLC" doesn't need a deployed agent — they need a Q Desktop session connected to the Biomni Gateway. But a hospital system running clinical decision support for 10,000 patients/day needs a production agent with guardrails, audit logs, and SLAs.

---

### Q3: Are we duplicating capabilities between MCP servers and catalog agents?

**Options considered:**
- A) MCP servers as thin proxies over deployed agent Gateway tools (no duplication, but requires deployment)
- B) Shared tool library with two entry points (MCP server + agent both import from same code)
- C) MCP servers ARE the canonical tools, agents consume them via Gateway

**Decision:** **Option A for short term, converging toward C long term.** The current architecture already supports this — AgentCore Gateway IS an MCP server. Agent 28 already demonstrates this pattern.

**Why:** Agent 28's Biomni Gateway is already an MCP endpoint. Any MCP client (Q Desktop, Co-work, another agent) can connect to it. We don't need to build separate MCP servers — the deployed Gateway tools ARE the MCP tools. The "thin proxy" is already built into AgentCore.

---

### Q4: Should the HCLS Toolkit also expose itself as a plugin (like the AWS Agent Toolkit)?

**Decision:** Yes. Same plugin format, registered as a separate marketplace.

**Why:** Builders should be able to `install aws-agents` (how to build on AWS) AND `install hcls-agents` (what to build for HCLS). Composable, not competing.

---

### Q5: Can our plugin support multiple AI coding assistants?

**Research findings:**

| Surface | Skill format | MCP support | Distribution |
|---------|-------------|-------------|--------------|
| Claude Code | `.claude-plugin/` + SKILL.md | `.mcp.json` (stdio) | Git marketplace |
| Claude Co-work | SKILL.md with frontmatter | App UI config (stdio + HTTP) | Plugin registry |
| Amazon Q Desktop | SKILL.md in `~/.quickwork/skills/` | Settings → Capabilities (stdio + SSE) | Manual file + server |
| Kiro | POWER.md + steering/ | `mcp.json` in power dir | Local path |
| Codex | `.codex-plugin/` + SKILL.md | Similar to Claude Code | Git-based |

**Decision:** Build skills as SKILL.md (shared content), package with thin adapters per surface. MCP servers are already universally portable.

**Why:** The CONTENT is portable. A well-written SKILL.md works across all surfaces with minor frontmatter adjustments. MCP servers work everywhere with zero adaptation. Only the distribution packaging differs — and that's a thin wrapper.

---

### Q6: What about non-technical users accessing HCLS workflows through Q Desktop / Co-work?

**Key insight from platform research:**
- Both Q Desktop and Co-work support MCP servers
- Both support SKILL.md-style workflow guidance
- Neither has enterprise admin-push (yet)
- Both expose custom tools to users via natural language — no coding required

**Decision:** The HCLS Toolkit should produce MCP-accessible domain tools (deployed to AgentCore) that end-user platforms can connect to directly. This answers the market question about "industry-specific modules."

**Why:** A researcher in Q Desktop who connects to the HCLS Biomni Gateway gets 30+ biomedical database tools accessible via natural language. No agent deployment needed on their end. The Gateway IS the industry module.

---

### Q7: Should we focus on the "product" (catalog) or the "developer experience" (plugins)?

**Decision:** Both, but cleanly separated.

**Why:** They serve different audiences and have different lifecycles:
- Product (catalog) = what gets deployed to production, serves end-users
- Developer experience (plugin) = what helps builders create/customize/deploy agents faster

The plugin references the catalog but doesn't duplicate it. The catalog benefits from the plugin's skills but doesn't depend on them.

---

### Q8: What's the relationship between this effort and the ongoing v1→v2 migration?

**Decision:** Complementary, not dependent. Short and medium term work proceeds without waiting for migration. Long-term full decomposition depends on agents being on v2.

**Why:** 
- Skills can be written against the target v2 architecture now (they're knowledge, not code)
- MCP configs can reference already-deployed v2 agents (28, 35, 36)
- As migration delivers more v2 agents, each immediately gains a skill + MCP endpoint
- The two workstreams have natural handoff: migration delivers the agent, this roadmap delivers the portable interface

---

### Q9: How do multi-agent workflows get assembled?

**Options considered:**
- A) Hardcoded supervisor agents (like the existing cancer biomarker discovery supervisor)
- B) Static workflow configs (Step Functions, DAGs)
- C) Dynamic orchestration via AgentCore Registry semantic search

**Decision:** **C — dynamic orchestration via AgentCore Registry.** Existing supervisor patterns (A) continue to work for well-defined workflows, but the primary pattern going forward is Registry-driven discovery.

**Why:** AgentCore Registry already supports this today:
- Agents register with rich descriptions (MCP server schemas, A2A agent cards, skill definitions)
- `SearchRegistryRecords` API does semantic search across registered records
- An orchestrator agent discovers and connects to capabilities at runtime — zero hardcoded integrations
- Record types: MCP, A2A, AGENT_SKILLS, CUSTOM — covers all catalog agent types
- Approval workflow ensures only validated agents are discoverable

**What this means for the HCLS toolkit:**
- Each catalog agent registers in the HCLS Registry on deployment
- New agents become instantly available to workflows without redeploying the orchestrator
- Complex HCLS workflows (biomarker discovery, patient genomic analysis, drug research pipelines) compose dynamically from registered agents
- End-user platforms (Q Desktop, Co-work) could also search the Registry to discover available HCLS capabilities

**The architectural progression:** Static supervisor (today) → Registry-discovered dynamic orchestration (target). Both coexist — static for deterministic pipelines, dynamic for exploratory workflows.

---

## What We Ruled Out

| Option | Why we ruled it out |
|--------|---------------------|
| Rebuilding agents AS plugins | Agents serve production users; plugins serve developers. Different concerns. |
| Creating standalone HCLS MCP servers from scratch | AgentCore Gateway already acts as MCP server. Don't build what exists. |
| Waiting for migration to complete before starting | Short-term packaging doesn't depend on v2 agents. |
| Single format for all surfaces | Formats aren't standardized across platforms. Accept thin adapters. |
| Replacing catalog agents with skills | Skills can't provide scale, compliance, or determinism. Agents are still needed for production. |

---

## Key Architectural Insight

The three catalog agents that already demonstrate the target pattern:

| Agent | What it proves |
|-------|---------------|
| **Agent 28** (Biomni) | AgentCore Gateway = MCP server. Any client connects directly. |
| **Agent 35** (OLS/Terminology) | Custom MCP server deployed to AgentCore Runtime. Managed hosting for MCP tools. |
| **Agent 36** (C4LS) | Strands `AgentSkills` loads SKILL.md + external MCP connectors. Skills and tools compose at runtime. |

And the AgentCore Registry samples demonstrate the orchestration pattern:

| Sample | What it proves |
|--------|---------------|
| **discovery-and-invocation-at-runtime** | Orchestrator discovers MCP + A2A agents via semantic search, connects dynamically, executes — zero hardcoded integrations |
| **registry-skills-dynamic-discovery** | Agent discovers and loads SKILL.md from Registry at runtime, installs dependencies, executes task |
| **publish-agentcore-tools-in-registry** | MCP servers and A2A agents register themselves with full connection metadata |

**The full architecture is proven across existing code.** The transformation is assembling these patterns into a coherent HCLS platform, not inventing something new.

---

## The One-Line Pitch

> The HCLS Agents Toolkit becomes a library of healthcare domain capabilities — deployable as production agents, consumable as developer skills, and connectable as MCP tools — serving builders in their IDEs, researchers in Q Desktop, and clinicians through production applications.
