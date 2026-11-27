# Oncology Semantic Hub — Feature Backlog

**Status: LIVING DOC.** Candidate features grouped by category. Add rows freely; fill `Priority` during
ranking. IDs are stable (gaps from removed/subsumed items are intentional). Baseline: **v1.0.0** (`CHANGELOG.md`).

**Size** S/M/L · **Status** idea·planned·design·in-progress·done·deferred · **Priority** (blank until ranked).

---

## Category A — Oncology Semantic Hub (domain capabilities)
Enhancements to *this* hub as a product — new tools, modalities, and personalization for oncology research.

| # | Feature | Size | Status | Priority | Notes / design ref |
|---|---|---|---|---|---|
| 3 | Human-in-the-loop context graph (self-improving hub) | L | design | | `docs/phase3-context-graph-design.md`. User context as `[UserContext]` tier; measured lift. |
| 9 | Compute/statistics tool for the agent (Fisher's, correlations) | M | idea | | Closes the "grounds data but estimates the stat" gap (Fisher p-value demo). |
| 10 | Drug brand→generic resolution tool | S | idea | | Tool-gap surfaced by benchmark (Tagrisso/Herceptin fail); DrugBank/RxNorm alias. |
| 14 | New data modality — medical imaging (radiology/pathology) | L | idea | | Process/synthesize imaging (DICOM/WSI), harmonize into hub, agent-surfaceable. RODA: CAMELYON, CHIMERA, RADIANT. Imaging-AI pipeline → features as case/Neptune properties. |
| 22 | Remote MCP server for custom Neptune + Athena tools (Quick Desktop) | M | in-progress | | **BUILT + DEPLOYED + VALIDATED.** `mcp-servers/agentcore-runtime/oncology-hub-data/` — FastMCP on AgentCore Runtime (serverProtocol=MCP, CUSTOM_JWT reusing OLS Cognito), 4 read-only tools reusing `hub_core.{queries,schema,guards}`; deploy.py (read-only IAM + Lake Formation grants + hub_core bundling + OLS-SSM preflight), get-token.sh, refresh-token.sh, cleanup.py, README. Validated via MCP client (JWT: tools/list + all 4 tool success paths + guard rejections) AND a custom Strands agent AND **L3′** (`agentcore/l3_prime.py`: workflow+eval skills + oncology-hub-data + OLS MCP → reproduced L3's MONDO-anchored 144 genes + 82 EGFR patients, metric 1.0/1.0). Skills: `skills/oncology-semantic-hub-analysis` (domain, at _L3_PROMPT parity) + `skills/grounding-faithfulness-eval` (process, drift-guarded). KB (`knowledge_search`) = LOCAL MCP (`mcp-servers/aws-public/bedrock-kb-retrieval/`), per owner. Design: `docs/remote-mcp-server-design.md` §16-17. **Remaining:** owner Quick-harness test; delete orphaned failed runtime c0f1892e; live-verify refresh-token.sh + the local KB MCP. Relates to #21, #20, #23. |

## Category B — Bring-Your-Own-Data + Workflow Execution
Generic capability to discover, process, and onboard *any* dataset into a hub. (The #2/#11/#17 cluster.)

| # | Feature | Size | Status | Priority | Notes / design ref |
|---|---|---|---|---|---|
| 2 | HealthOmics workflow execution on discovered VCFs | L | planned | | **Owner: Nadeem (VCF/BAM lane — no duplication).** `docs/phase3-plan.md` §F2. 1000 Genomes VCF → VEP → S3 Tables → agent query. #17's onboarding skill hands off to this via the RAW_GENOMICS contract (`docs/skill-design-roda-onboarding.md` §8). |
| 11 | Multi-step workflow skills (build/run + query planning) | M | idea | | Skills for composing multi-step workflows. *Clarify scope during prioritization:* originally query-planning (multi_source/graph_multihop); overlaps the skill layer of #17. |
| 17 | HITL data-discovery + ETL-authoring skill (RODA → hub) | L | design | | **Design: `docs/skill-design-roda-onboarding.md`.** Agent-driven, generic onboarding of **tabular/relational** RODA datasets — discover (RODA MCP) → classify → author ETL → dry-run→approve→apply HITL gates → lake (+optional graph extension) → ontology-harmonize (OLS) → validate → register with agent. Goes *beyond* RODA MCP (discovery-only). Orchestrates existing `scripts/roda/` primitives; builds the codegen/generalized-graph-extension/validation/registration gaps. **VCF/BAM lane delegated to Nadeem (#2/#19)** — handoff contract only, no duplication. Realizes #11. |

## Category C — Benchmark Framework (Accelerator 2)
Measurement methodology, metrics, validation, and cross-model studies.

| # | Feature | Size | Status | Priority | Notes / design ref |
|---|---|---|---|---|---|
| 1 | Radar-chart metrics visualization (matplotlib PNG) | S | planned | | `docs/phase3-plan.md` §F1. Per-layer polygons across metric dimensions. |
| 4 | External-dataset validation — LAB-Bench DbQA2 | M | planned | | Run framework on `lab-bench.pdf` DbQA2 (`filter_dbqa2.py`); keep gated GT gitignored. |
| 5 | Statistical significance on L2-vs-L3 gap (McNemar, bootstrap CIs) | M | idea | | Paper-grade rigor (from publication review). |
| 6 | Human/expert validation of golden Q&A (inter-annotator κ) | M | idea | | Expert review of 84-Q GT; judge-vs-human agreement. |
| 7 | Complete 2×2 ablation metrics (L3a/L3b full custom scorer) | S | idea | | L3a native done (0.738); extend custom scorer + confirm L3b. |
| 15 | Cross-lab model comparison (frontier + open-weight on Bedrock) | L | idea | | Claude / Nova / Llama / DeepSeek / Mistral etc. Does the hub lift hold across models? Which gaps are model-invariant? (Absorbs the earlier "second model" item.) |
| 16 | Latency + total-AWS-cost as benchmark metric dimensions | M | idea | | New axes alongside correctness/faithfulness/reproducibility: response latency (L2 vs L3) + total cost (Bedrock+Neptune+Athena+S3). Accuracy-vs-cost/latency tradeoff. |
| 23 | Real-time (single-response) metric computation — surface to users live | M | in-progress | | **Real-time path SHIPPED + independently reviewed/tested + live-verified on L3.** `agentcore/realtime_metrics.py` computes **grounding_rate** + **provenance-faithfulness** from one response (no GT, no extra LLM call), surfaced in `chat_ui.py` (badges + toggles) and emitted to CloudWatch (namespace `OncologySemanticHub/Metrics`, `Mode=realtime` invocation-ts / `Mode=batch` job-ts via `run_v2_benchmark.py --emit-metrics`). Both `PutMetricData` + EMF backends. Canonical scorer reuse → real-time == batch defs. Docs: `agentcore/README.md`, `docs/benchmark-report.md` §12b. **DEFERRED:** Quick Desktop integration — needs a Quick skill to make the Quick agent emit inline provenance tags (the only dependency). **Approach (2026-08-19):** the Quick skill emits tags (tool→tag map) AND computes the metric — prefer (A) bundling our deterministic `compute_realtime` as a skill script with a baked-in `"quick"` tool inventory (≈L3) if Quick supports skill scripts+code-exec (**VERIFY**); else (B) LLM self-report as a labeled live estimate + authoritative deterministic score post-hoc from observability. Also add a `"quick"` inventory to `provenance_faithfulness.VALID`. **FINDING (2026-08-20, live Quick test):** Quick did NOT execute the bundled skill script — it returned `grounding_rate=0.80 · provenance_faithfulness=1.0 (self-reported — script not executed)`. So approach (A)-via-skill-script is NOT available in Quick; the self-report (B) is near-circular/weak. **RESOLUTION:** deliver the deterministic scorer as an **MCP tool** (Quick runs MCP tools reliably — proven) — a small local stdio "provenance-eval" MCP server exposing `score_provenance(answer, inventory)`, reusing the same logic; the workflow skill instructs the agent to CALL that tool and report its result. See `docs/remote-mcp-server-design.md` §15. **DEMO DECISION (2026-08-20, owner):** do NOT build the MCP tool for the demo yet — use approach (B) **self-report** via a required step in `oncology-semantic-hub-analysis/SKILL.md` (exact grounding_rate/provenance_faithfulness formulas inline so the agent computes from its own tags, labeled `self-reported`); deterministic eval SKILL script remains for script-capable harnesses (Claude Code/CLI/L3′). MCP-tool path deferred to post-demo. Correctness/reproducibility stay batch. |
| 24 | Metadata catalog (`query_catalog`) as L3c enrichment layer | M | idea | | Realizes the **L3c** ablation (`docs/benchmark-report.md` §15): *"does an enriched metadata catalog close the L2→L3 gap without a graph?"* Candidate impl: **DLA Metadata-Builder** (`DLA-Data-Accelerators/02.Metadata-Builder` — Lambda+Bedrock generates business/column/rules metadata from Glue/CSV/Redshift/Unity/Snowflake). **Eval finding (2026-08-19): DLA works but uses far more tokens for the same result vs live `get_hub_schema`** → NOT adopted as the runtime schema mechanism. Retain for (a) the L3c ablation and (b) **governance/business-metadata enrichment** (owner/steward/classification/quality rules, column business definitions) that structural introspection can't provide; refresh on dataset onboarding (shared Glue catalog). Complementary to live `get_hub_schema` (structural), not a replacement. **NOT part of #22** (MCP deployment). |
| 25 | AgentCore Gateway + invocation interceptors for deterministic metrics | L | idea | | Deploy an **AgentCore Gateway** fronting the hub MCP servers/tools so **invocation interceptors** compute `grounding_rate` + `provenance_faithfulness` (and provenance-tag/citation checks) **deterministically, server-side, on every invocation** — instead of relying on the consuming agent/skill to run the scorer (which is prompt-adherence-dependent: Quick self-reported / scored a stale draft → wrong grounding_rate 1.0 vs 0.857). Removes the reliability gap and is the hard-guarantee replacement for the skill-side code-exec snippet. Also a natural home for per-user auth (#21) + governance/audit. **Interim:** the `oncology-semantic-hub-analysis` skill's code-execution snippet (hardened: prints tag_census/answer_tail, self-check). Relates to #23 (real-time metrics), #22 (MCP deploy), #21 (per-user auth/SSO). |

## Category D — Cross-cutting / Strategic
| # | Feature | Size | Status | Priority | Notes / design ref |
|---|---|---|---|---|---|
| 13 | Additional domain instance (beyond oncology) | L | idea | | Prove domain-agnostic accelerator (e.g., cardiology / rare disease). Exercises Category B end-to-end in a new domain. |

## Category E — Integration with parallel streams (collaborators)
Fold our accelerators into the team's unified semantic-layer framework rather than standalone solutions.

| # | Feature | Size | Status | Priority | Notes / collaborator |
|---|---|---|---|---|---|
| 18 | Integrate Stan's observability + governance into A2 (+ demo) | L | idea | | **w/ Stan.** Unify our dev-time benchmark (golden-set: correctness/reproducibility/grounding_rate/provenance-faithfulness) with Stan's runtime, no-golden-set grounding guardrail (pass/caution/fail). One grounding definition across dev+prod; add context-poisoning + calculation-gap (adversarial) checks. Impacts BOTH accelerator + demo. |
| 19 | Downstream bioinformatics workflow skill + RODA | L | idea | | **w/ Nadeem.** Skills-based, graduated-automation (step-by-step approval → config-driven autonomy) for RODA discovery → bioinformatics ETL (HealthOmics). Realizes Category B (#2/#11/#17) with Nadeem's HITL trust model. |
| 20 | Define A1 per semantic-hub architecture + patterns | M | idea | | **w/ Indradeep.** Align A1 to the enterprise semantic-layer construct (federated architecture, governance, quality, CI/CD) — position A1 as a reference implementation of the shared pattern, not a one-off hub. **Constraint (2026-08-13):** do **not** genericize A1 into a domain-agnostic shell — generic accelerators already exist. Differentiation = **therapeutic-area lens** (curated oncology datasets + ontologies to the forefront) + strong **BYOD**. Retain oncology flavour; **A1's degree of generality is NOT finalized** — resolve before any repositioning/refactor work. (Supersedes the earlier "method-ization / generalize A1" direction, which is on hold.) |
| 21 | Governed per-user DB access + **SSO** (custom tool vs MCP) + tenancy | L | design | | **Design: `docs/per-user-auth-design.md`.** Target: admin grants a user **SSO** access to the hub MCP servers with per-user identity/audit/governance — replacing today's single shared M2M Cognito client. Two layers: (A) authN via SSO/OIDC authorization_code → per-user JWT validated by AgentCore CUSTOM_JWT (Cognito+federation / IAM Identity Center / 3rd-party IdP); (B) authZ via `sts:AssumeRole` per request in the server (session=user) → per-user CloudTrail + Lake Formation data scoping.

---

## Parking lot (unshaped ideas — promote when ready)
- _(add here)_

## Removed / merged
- **#8** Cost/latency analysis → merged into **#16** (now benchmark metric dimensions).
- **#12** Second subject model → absorbed into **#15** (cross-lab comparison).

## Recently shipped (v1.0.0)
- Two accelerators; oncology reference hub; de-accounted + tested repo; 23 unit tests; deploy path live-verified. See `CHANGELOG.md`.
