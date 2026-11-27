# Oncology Semantic Hub — MCP Servers + Skills + Quick Desktop Integration Design

> **Status:** DRAFT v3 — supersedes v2. Scope reduced after framework alignment ([`docs/proposals/framework-design.md`](../../docs/proposals/framework-design.md)).
> **Branch:** `feat/oncology-hub-mcp-skills` (to be created)
> **Date:** June 1, 2026

---

## 1. Goal

Make the existing oncology semantic hub consumable from **Amazon Quick Desktop** (and other MCP-compatible clients) by packaging two AWS MCP server configs and one domain skill into the existing HCLS framework.

No agent code is written. No existing code is refactored. The Streamlit reference at `oncology_semantic_hub/agent/app_local.py` stays as-is.

---

## 2. The four-component model

| # | Component | What it is | Status |
|---|-----------|------------|--------|
| 1 | **Semantic hub** | Neptune Analytics graph `<your-graph-id>` (174,742 nodes, 4M edges) + Athena database `oncology_semantic_hub` + S3 storage | ✅ Built and live (out of scope for this design) |
| 2 | **MCP servers** | `awslabs.amazon-neptune-mcp-server` + `awslabs.aws-dataprocessing-mcp-server` — published by AWS Labs, configured by us | This design |
| 3 | **Skill** | `oncology-semantic-hub-analysis` — domain knowledge teaching consuming agents how to use the MCP servers against this hub | This design |
| 4 | **Agent** (consumer) | **Amazon Quick Desktop** for this design. Claude Code / Kiro / Codex / AgentCore-deployed agents are future component-4 swaps that should work with no changes to 2 or 3 | Quick Desktop wiring is in scope |

Components 2 and 3 are designed once. Component 4 swaps freely.

---

## 3. Artifacts to produce

| Artifact | Path | Type | Estimate |
|----------|------|------|----------|
| Neptune MCP config | `mcp-servers/aws-public/amazon-neptune/.mcp.json` + `README.md` | New (config only) | 30 min |
| Data Processing MCP config | `mcp-servers/aws-public/aws-dataprocessing/.mcp.json` + `README.md` | New (config only) | 30 min |
| Domain skill | `skills/oncology-semantic-hub-analysis/SKILL.md` + `references/` | New (markdown) | 4–6 hours |
| Plugin manifest entries | `plugins/hcls-agents/.mcp.json` (add 2 entries) | Update | 10 min |
| Quick Desktop setup section | `platforms/amazon-quick/README.md` (add hub section) | Update | 30 min |
| Claude Code adapter | `platforms/claude-code/.mcp.json` (add 2 entries) | Update | 10 min |
| Kiro adapter | `platforms/kiro/mcp.json` (add 2 entries) | Update | 10 min |
| Codex adapter | `platforms/codex/config.toml` (add 2 entries) | Update | 10 min |
| Validation report | `oncology_semantic_hub/docs/quick-desktop-validation.md` | New | 1 hour (after Quick Desktop test) |

**Total estimate: ~1 day of focused work**, of which the SKILL.md authoring is the only intellectual lift.

---

## 4. MCP server configurations

### 4.1 Neptune (`mcp-servers/aws-public/amazon-neptune/.mcp.json`)

```jsonc
{
  "mcpServers": {
    "amazon-neptune": {
      "command": "uvx",
      "args": ["awslabs.amazon-neptune-mcp-server@latest"],
      "env": {
        "NEPTUNE_ENDPOINT": "neptune-graph://<your-graph-id>",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

**Smoke-tested in this session.** Tools the consuming agent will see (verified):
- `run_opencypher_query(query)` — returns parsed JSON results
- `get_graph_schema()` — labels and edge types
- `get_graph_status()` — `Available` / `Unavailable`

**Required IAM** (the consuming user's role, not us): `neptune-graph:ReadDataViaQuery` on the graph ARN. This is consumer-side — we don't provision it for them.

### 4.2 Data Processing (`mcp-servers/aws-public/aws-dataprocessing/.mcp.json`)

```jsonc
{
  "mcpServers": {
    "aws-dataprocessing": {
      "command": "uvx",
      "args": [
        "awslabs.aws-dataprocessing-mcp-server@latest",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

`--allow-sensitive-data-access` is required: without it, `manage_aws_athena_query_executions(operation="get-query-results")` is blocked. The data is public TCGA, not PHI, so the flag's intent doesn't apply. We deliberately do **not** enable `--allow-write`.

**Smoke-tested in this session.** Tools the consuming agent will see (verified):
- `manage_aws_athena_query_executions` — start/stop/get queries, get results, polling internal
- `manage_aws_athena_databases_and_tables` — Glue catalog metadata for `oncology_semantic_hub`
- `manage_aws_athena_workgroups` — uses `primary` workgroup
- 30+ other Glue/EMR tools we don't need but are bundled

**Required IAM** (consumer-side): `athena:StartQueryExecution`, `athena:GetQueryExecution`, `athena:GetQueryResults`, `glue:GetTable*`, `glue:GetDatabase*`, plus S3 read on the data bucket and S3 write on the `athena-results/` prefix for query result staging. Spelled out in `mcp-servers/aws-public/aws-dataprocessing/README.md`.

---

## 5. Skill: `oncology-semantic-hub-analysis`

### 5.1 Skill name

`oncology-semantic-hub-analysis` — discoverable, names the asset, follows the broader-pattern of existing skills (`biomarker-database-analysis`, `biomarker-pathway-analysis`).

### 5.2 SKILL.md structure (matches existing skills)

```yaml
---
name: oncology-semantic-hub-analysis
description: Use when a researcher asks about cancer biomarkers, TCGA patient mutations,
  drug-gene relationships in oncology, pan-cancer driver gene analysis, or pathway-level
  questions that span PrimeKG and TCGA. Combines the Neptune knowledge graph (PrimeKG +
  TCGA + ClinVar/COSMIC) with the Athena patient data lake (TCGA mutations across 33
  cancer types).
---
```

### 5.3 SKILL.md body (sections)

1. **When to use this skill** — concrete trigger phrases (drug targets for breast cancer mutations, top mutated genes in TCGA-GBM, PPI neighbors of glioblastoma genes, etc.)
2. **MCP servers used** — `amazon-neptune` and `aws-dataprocessing`. Brief note that they're complementary: graph for relationships, lake for patient-level counts.
3. **Discover schema first** — instruct the agent to call `get_graph_schema()` and `manage_aws_athena_databases_and_tables(operation="list-table-metadata", ...)` at session start. Don't memorize.
4. **Workflow patterns** with sample queries:
   - Pattern A: graph-only (drug targets, pathway membership, disease associations)
   - Pattern B: lake-only (mutation counts per cancer type, variant impact distribution)
   - Pattern C: cross-system (top mutated genes → drug targets in graph)
   - Pattern D: multi-hop (4-hop traversals like "drugs targeting PPI neighbors of GBM genes")
5. **Known caveats** — 6 approximate TCGA→MONDO mappings, 227 unmatched gene names, BRCA1 has 0 `drug_protein` edges in PrimeKG (cite our existing `data/golden_dataset.json` validation work).
6. **Quality conventions** — always use partition pruning (`WHERE project_id='TCGA-XXX'` for Athena), always ground Neptune queries in `get_graph_schema` results, never invent gene/drug names not returned by tools.

### 5.4 References (loaded on demand)

```
skills/oncology-semantic-hub-analysis/
├── SKILL.md                    ← main skill (~5-6KB)
└── references/
    ├── schema-summary.md       ← detailed graph + lake schema (lifted from agent/main.py:get_hub_schema())
    ├── sample-queries.md       ← 12 verified queries from data/golden_dataset.json
    └── caveats.md              ← cross-system ontology misalignment (lifted from PROJECT-STATUS.md)
```

Content for these files already exists — we extract from `oncology_semantic_hub/docs/PROJECT-STATUS.md` and `oncology_semantic_hub/data/golden_dataset.json`. No new domain research required.

### 5.5 What the skill is NOT

- Not a system prompt for a specific agent (agnostic to component 4)
- Not Quick Desktop-specific (works for Claude Code, Codex, etc.)
- Does not include visualization instructions (visualizations are Streamlit-only, out of scope)

---

## 6. Quick Desktop wiring

### 6.1 Update `platforms/amazon-quick/README.md`

Add a section under "Quick Setup → Step 1: Install Skills":

```markdown
| Oncology Semantic Hub Analysis | `skills/oncology-semantic-hub-analysis/SKILL.md` | Cancer biomarker queries combining PrimeKG + TCGA |
```

Add a section under "Step 4: Add MCP Servers":

```markdown
| Server | Transport | Command | Notes |
|--------|-----------|---------|-------|
| Amazon Neptune | stdio | `uvx awslabs.amazon-neptune-mcp-server@latest` | Set `NEPTUNE_ENDPOINT=neptune-graph://<your-graph-id>`, `AWS_REGION=us-west-2` |
| AWS Data Processing | stdio | `uvx awslabs.aws-dataprocessing-mcp-server@latest --allow-sensitive-data-access` | Set `AWS_REGION=us-west-2`. Requires AWS credentials with read access on Athena database `oncology_semantic_hub` |
```

Add a "Test" section with two verifiable queries:

```markdown
| Question | Expected behavior |
|----------|-------------------|
| "How many disease nodes are in the PrimeKG knowledge graph?" | Skill routes to amazon-neptune → `run_opencypher_query` → returns 17,080 |
| "What are the top 5 most frequently mutated genes in TCGA-BRCA?" | Skill routes to aws-dataprocessing → returns TP53 (330), PIK3CA (328), TTN (182), CDH1 (128), GATA3 (125) |
```

### 6.2 No code, no auth gateway

For the first iteration: the user brings their own AWS credentials configured locally. The two MCP servers (running locally via uvx as stdio processes) use those credentials. This matches how the existing `aws-healthomics` server in `platforms/amazon-quick/` works.

If the audience expands beyond AWS-credentialed users (e.g., external pharma collaborators without AWS accounts), an AgentCore Gateway in front of Neptune/Athena would be needed. **Out of scope for this design**; tracked separately if/when it comes up.

---

## 7. Repository updates

```
mcp-servers/aws-public/
├── amazon-neptune/                 ← NEW
│   ├── .mcp.json
│   └── README.md
└── aws-dataprocessing/             ← NEW
    ├── .mcp.json
    └── README.md

skills/oncology-semantic-hub-analysis/   ← NEW
├── SKILL.md
└── references/
    ├── schema-summary.md
    ├── sample-queries.md
    └── caveats.md

plugins/hcls-agents/.mcp.json            ← UPDATED (add 2 entries)
platforms/amazon-quick/README.md         ← UPDATED (hub section)
platforms/claude-code/.mcp.json          ← UPDATED (add 2 entries)
platforms/kiro/mcp.json                  ← UPDATED (add 2 entries)
platforms/codex/config.toml              ← UPDATED (add 2 entries)

oncology_semantic_hub/docs/
└── quick-desktop-validation.md          ← NEW (validation report after testing)
```

**Files that DO NOT change:**
- `oncology_semantic_hub/agent/main.py` — Strands `@tool` functions stay as-is; reference implementation
- `oncology_semantic_hub/agent/app_local.py` — Streamlit demo on port 8501, unchanged
- `oncology_semantic_hub/benchmark/*` — used as validation harness, no logic change
- `oncology_semantic_hub/data/golden_dataset.json` — frozen ground truth, source for skill's sample queries

---

## 8. Validation plan

### 8.1 Smoke test (during build)

For each MCP server, after configuring:

```bash
# From a Claude Desktop or mcp-inspector session, with the new config loaded
$ /tools  # confirm both servers attach
$ run_opencypher_query "MATCH (n) RETURN count(n)"  # expect 174,742
$ manage_aws_athena_workgroups operation=list-work-groups  # expect 'primary'
```

Already verified in this CLI session. Re-verifying in Claude Desktop and Quick Desktop is the deliverable.

### 8.2 Skill effectiveness (using existing benchmark)

The 12-question golden dataset at `oncology_semantic_hub/data/golden_dataset.json` is our pre-built validation harness.

**Method:**
1. Set up Quick Desktop with the new hub skill + 2 MCP servers
2. Ask each of the 12 benchmark questions through Quick Desktop
3. Capture the responses
4. Run them through `oncology_semantic_hub/benchmark/run_evaluation.py` (the existing LLM-as-judge pipeline)
5. Compare correctness to the L3 baseline (0.958 from the benchmark MVP)

**Pass criteria:** correctness within ±0.05 of L3. If lower, investigate before merging.

This validates that **routing through skill + MCP produces equivalent answers** to the hand-rolled Strands path. It's not a new benchmark; it's reusing the one we already trust.

### 8.3 Cross-platform sanity (lighter)

After Quick Desktop passes, the same skill + 2 MCP servers should work in Claude Code with no further authoring. We do a single spot-check (one cross-system question through Claude Code) to confirm. If it works, we don't run the full benchmark there — we know the architecture is sound.

---

## 9. Open questions

1. **Skill path for Quick Desktop.** The Quick adapter README mentions both `cp -r skills/ ~/.quickwork/skills/` and per-skill installation through Settings. For our case, do we recommend: (a) install just `oncology-semantic-hub-analysis` standalone, or (b) install all HCLS skills as a bundle? My vote: (a) for the customer demo (less surface area to explain). (b) for AWS-internal users.

2. **Schema in skill vs schema from MCP.** The skill's `references/schema-summary.md` documents the schema, but the agent can also discover it live via `get_graph_schema` and `list-table-metadata`. Which should we instruct the agent to prefer? My vote: live discovery as primary, schema-summary.md as fallback / overview. This avoids drift if PrimeKG is reloaded.

3. **Tool autoApproval.** Quick Desktop and Kiro/Claude Code allow per-tool approval lists. For read-only safe tools (`get_graph_schema`, `run_opencypher_query`, `manage_aws_athena_query_executions` with SELECT-only) we can pre-approve. We should NOT pre-approve write paths (which we're already blocking via flags + IAM, but defense in depth). The MCP configs in §4 should include `autoApprove` lists matching the read-only tools.

4. **Naming of the `feat/` branch.** I proposed `feat/oncology-hub-mcp-skills`. Open to other suggestions — this is short-lived (~1 day) so naming doesn't matter much.

---

## 10. Out of scope for this design

- Refactoring `oncology_semantic_hub/agent/main.py` or `app_local.py` (the Streamlit reference stays).
- Deploying any new agent to AgentCore Runtime.
- Authenticating non-AWS users (would require AgentCore Gateway).
- Adding the OLS MCP server (`mcp-servers/agentcore-runtime/ontology-lookup-service`) into the hub skill — could be a follow-up iteration if cross-ontology questions become a priority.
- New benchmark questions or eval methodology — we use the existing 12-question MVP unchanged.

---

## 11. Migration steps (after approval)

1. Create branch `feat/oncology-hub-mcp-skills` from `main`.
2. Add the two `mcp-servers/aws-public/` config files + READMEs.
3. Author the skill (SKILL.md + references/) by extracting from existing project docs.
4. Update plugin and platform manifests with the two new MCP entries.
5. Update `platforms/amazon-quick/README.md` with the hub section.
6. **Validate**: install on Quick Desktop, run the 12 benchmark questions, score with `run_evaluation.py`, compare to L3 baseline.
7. Write `oncology_semantic_hub/docs/quick-desktop-validation.md` with the comparison.
8. Spot-check on Claude Code (one cross-system question).
9. Open PR.

The whole sequence should fit in one day's focused work.
