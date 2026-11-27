# Session Handoff — 2026-08-12 (context reload)

## Where we are
Repo `oncology_semantic_hub` (public aws-samples target; internal gitlab: gitlab.aws.dev/hpoonawa/oncology-semantic-hub).
Two accelerators, **v1.0.0**, de-accounted + tested + check-in-ready. Now in **strategy/positioning phase** (not
active feature-building) — aligning with the team's enterprise semantic-layer framework before publish.

## The two accelerators (settled positioning — "method, not sample data")
- **A1 — Semantic Hub Starter + BYOD:** KG + L3 constructs (graph traversal + ontology harmonization) + repeatable
  BYOD pipeline (RODA open data + customer cohorts). TCGA = reference implementation, NOT the value (table stakes).
  Governed per-user DB access by design (custom boto3 tool; MCP servers can't inject per-request creds — Taylor Riggan note).
- **A2 — Benchmark Framework:** measures correctness · reproducibility · grounding/faithfulness across L0→L1→L2→L3.
  **Operates today in "attempt-and-attribute" mode (agents attempt + tag provenance; NO gating).** Gating/CI-gate =
  FUTURE (user corrected me on this — do not call it a CI-gate today). Grounding metric = **superset of Bedrock
  Contextual Grounding** (tool-provenance across lake/graph/OLS/KB/RODA; tier-aware; no KB/Gateway dependency) +
  provenance-faithfulness (fabricated-grounding detection).

## Headline results (v1.0.0, Claude Sonnet 4.5, temp0, 84-Q)
Correctness L0 .131/L1 .405/L2 .667/**L3 .798**; custom-F1 L2 .728/L3 .834; grounding .26/.66/.99/**1.0**;
reprod-correct .165/.417/.632/**.733**; self-agreement ~.71/.73/.70/.75. 2×2 ablation: L2 .667 / L3b .690(flat+OLS) /
L3a .738(graph−OLS) / L3 .798 → **graph is the primary driver**. Faithfulness ~0.99 all tiers (null discriminator).
Root-cause of L3<100%: brand→generic drug gap (#10), multi-step planning frontier (#11), reconciliation MONDO
name-fan-out. GT fixed for survival negatives (neg_062/063 → answerable; data IS in hub via case.days_to_death).

## Team feedback driving current work
- **Lisa:** A1-as-TCGA isn't enough (table stakes); wants substantial persona demos; endorses the benchmarking accelerator.
- **Stan:** vision = governed semantic layer as enterprise construct (federated/governance/quality/CI-CD/observability).
  His observability = Bedrock Contextual Grounding (KB-literature only, Bedrock-KB only, Gateway-dependent) — OURS is broader.
- **Nadeem:** graduated automation (step-by-step approval → config-driven) via skills; offered hands-on dev.
- **Indradeep:** agreed; will define the semantic-layer architecture/patterns.
- **Integration mandate:** combine our benchmark + Stan's observability + Chaitanya's benchmarking app + Ariella/Michael's
  "full framework" into ONE cohesive framework, not silos. Chaitanya's + Ariella/Michael's scopes are UNKNOWN (user to gather).

## Deliverable docs created/updated this session (all in docs/)
- **accelerator-positioning.md** — CRISP EXEC-LEVEL strategic doc (current + future position, NO names/tactical tasks).
  References (as md links) whitepaper-4.1, next-steps-onepager, backlog.
- **exec-summary-lead-team.md** — shareable for Lisa & Indradeep; intro = combined "what-it-is + work-toward" paras for
  A1/A2 + collaborators; differentiation (grounding superset, BYOD method, governed per-user access); the ask.
- **next-steps-onepager.md** — TACTICAL live tracker: 7-day alignment sprint (checkboxes) + per-collaborator outreach
  snippets + meeting TODOs. Objective: complete alignment in 7 working days.
- **backlog.md** — 21 features in 5 categories: A Oncology-Hub (3,9,10,14) · B BYOD+Workflow (2,11,17) ·
  C Benchmark (1,4,5,6,7,15,16) · D Cross-cutting (13) · E Integration (18 Stan, 19 Nadeem, 20 Indradeep, 21 governed-access).
  Removed/merged: #8→#16, #12→#15.
- **phase3-plan.md**, **phase3-context-graph-design.md** — Phase 3 designs (radar chart; HealthOmics workflows;
  human-in-the-loop context graph w/ literature synthesis — Eywa/PAHF/EpisTwin/Arize; answers to 5 design Qs + user-context×question-set).
- **sales-enablement-brief.md** — two-accelerator framing (A1 sharpened to method+BYOD; governed-access bullet added).
- **benchmark-report.md** — THE technical report (§1-20: exec summary, methodology, definitions, results, root-cause,
  §18 why-not-100%, §19 tool-gap identification, §20 planning-frontier/skills). §15 has graph-vs-ontology clarification.
- **demo-golden-thread-v4.md** — 4-question EGFR-GBM demo (Q1-2 L2vsL3, Q3-4 L0vsL3).
- Docs cleaned: 12 essential + docs/archive/ (19 historical); docs/README.md indexes current set.

## Repo structure (post-cleanup, v1.0.0)
agentcore/ (agent, deploy.py, run_v2_benchmark.py, run_agentcore_eval.py, chat_ui.py, kb/, README, agent_config.example.json) ·
evaluation/ (scorers: scoring.py, judge.py, provenance_faithfulness.py, config.py, README) ·
ground_truth/ (golden_v2.json=84Q active, FROZEN_phaseA, golden_dataset_v1, adversarial, faithfulness_stress, gen scripts) ·
scripts/ (01-16 pipeline + roda/, all env-driven via _config.py) · tests/ (23 unit tests, all pass) ·
docs/ + docs/archive/ · output/ (gitignored, 6 result files) · data/ (gitignored). VERSION=1.0.0, CHANGELOG.md, .env.example.

## Critical technical facts
- **De-accounted:** zero hardcoded account(942514891246)/graph(g-8aalvitz38) in committable files; _config.py fail-loud
  require(); deploy.py injects SEMHUB_GRAPH_ID/ATHENA_OUTPUT at runtime; .gitignore covers agent_config*/.env/output/data.
- **Deploy path live-tested post-refactor:** fresh L3 (l3_dc121cb6) deployed + smoke-tested (lake+graph both 1.0).
- **Current deployed agents (us-west-2):** L3 agent_config.json→l3_dc121cb6-nXciap9kmL (new, tested); L2 l2_8ddb496f;
  L0 l0_745ab7cd; L0-web l0_web_5223ddc9 (works, web_search fires via us-east-1 gateway web-search-gateway-btxsvamkpk);
  L1, L3a, L3b configs present. All agent_config*.json gitignored.
- **Golden dataset:** ground_truth/golden_v2.json (84Q, survival GT fixed 2026-08-10).
- **INVOKE lesson:** ad-hoc invoke scripts need Config(read_timeout=400,connect_timeout=15,retries max_attempts=0); fresh uuid session per call.

## NEXT STEPS (immediate)
1. User runs the 7-day alignment sprint (see next-steps-onepager.md) — syncs w/ Indradeep/Stan/Chaitanya/Ariella-Michael/Nadeem.
2. **Biggest unknowns to unblock:** Chaitanya's benchmark-app scope + Ariella/Michael's framework scope → then I turn the
   integration-map placeholders into a concrete plan.
3. Optional pending: apply md-link treatment to cross-refs in exec-summary + one-pager + docs/README (positioning doc done).
4. Post-alignment highest-leverage build: #18 (A2 + Stan observability, add context-poisoning) + one RODA-BYOD persona demo.

## Working-style notes (owner preferences)
Confirm-don't-speculate; all code changes reviewed + tested (golden rule); keep docs current; separate durable strategy
(positioning) from tactical (one-pager); crisp exec-level writing; no people-names/tasks in the positioning doc.
