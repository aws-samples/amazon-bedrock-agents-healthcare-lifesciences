# Phase 3 — Feature Plan (design tracks, iterate before execution)

**Status: PLANNING (2026-08-11).** Three features extending the two accelerators. Each is a sizable
design track; this doc captures scope, grounding, candidate data, and open questions so we can iterate
on design before building. Versioning: see `VERSION` + `CHANGELOG.md`.

> Baseline for Phase 3 = **v1.0.0** (two accelerators, oncology reference, de-accounted, tested).

---

## Feature 1 — Radar chart metrics visualization  → target v1.1.0
**Accelerator 2 · Size: Small · Risk: none**

### Scope
After a benchmark run, render a **matplotlib radar/spider PNG** to `output/`. Axes = metric dimensions
(correctness, reproducibly-correct, self-agreement, grounding_rate, faithfulness); one polygon per layer
(L0→L3). The L3 polygon visibly encloses the others — the "capability shape" of the ladder.

### Settled decisions
- **matplotlib PNG** (not interactive) — matches existing report assets, zero new deps.
- Per-layer overlay (not per-category).
- Metrics already 0–1 → no normalization.
- Reads `output/v2_benchmark_results.json` + native eval files.

### Open questions
- Include L3a/L3b ablation polygons, or just L0–L3? (probably a separate ablation chart)
- One combined chart vs per-category small-multiples?

### Build note
New file `evaluation/visualize.py` (or extend the report generator). Add a unit test that asserts the PNG
is produced + non-empty. Output → `output/` (gitignored).

---

## Feature 2 — Downstream workflow execution (HealthOmics on discovered VCFs)  → target v1.2.0
**Accelerator 1 extension · Size: Large · Risk: high (cost, async, IAM, safety)**

### Scope
Agent discovers a RODA dataset containing VCFs → triggers an **AWS HealthOmics** workflow (VEP + ClinVar
annotation) → annotated variants land in **S3 Tables / Athena** → become agent-queryable. This is the
retrieval→**action** shift, and it enriches the hub with newly-processed data.

### Grounding (proven pattern — already in `roda_oncology_hub_complete_reference.md` §HealthOmics)
```
RODA S3 (raw VCF/BAM) → HealthOmics Workflow (VEP + ClinVar) → S3 Tables (Iceberg/Parquet) → Agent (Athena NL)
```
- Ref A: *Accelerating genomics variant interpretation with AWS HealthOmics and Amazon Bedrock AgentCore*
  (Sandanaraj, Lee & Poonawala, Nov 2025) — the end-to-end pattern.
- Ref B: *From Prompt to Pipeline: AI-Powered Bioinformatics Workflow Development with Kiro and AWS HealthOmics*
  (Mar 2026) — the HealthOmics MCP server + Kiro Power for authoring/deploying WDL/Nextflow, and the
  HealthOmics MCP for NL workflow management. Use this to author/deploy the annotation workflow.

### Candidate RODA datasets (Accelerator 1 addition — pick ONE to start)
| Dataset | Input | Scale | Workflow | Why |
|---|---|---|---|---|
| **1000 Genomes** | VCF (already called) | 85M variants / 2,500 samples | **VEP annotation only** | **Cleanest start** — no variant-calling, annotation-only, public |
| ICGC PCAWG | WGS VCFs | 2,400 genomes | VEP + ClinVar | Bigger, us-east-1, cancer-specific |
| Kids First | WGS BAM/CRAM | 30+ studies | Alignment + calling + VEP | Heaviest (full calling, dbGaP-controlled) |

**Recommendation:** start with **1000 Genomes VCF → VEP annotation** (annotation-only, open, smallest blast
radius) as the reference workflow; document ICGC/Kids-First as scale-up paths.

### Open design questions
- **Workflow source:** Ready2Run vs author a WDL/Nextflow VEP workflow via the HealthOmics Kiro Power? (author gives a reusable asset; Ready2Run is faster to demo)
- **Trigger + safety:** workflows cost money + run for hours → **human approval gate required** (shares the HITL foundation with Feature 3). Agent *proposes*, human *approves*, then execute.
- **Async tracking:** how does the agent report a multi-hour run's status? (HealthOmics MCP `GetRun` polling / EventBridge)
- **Result routing:** annotated output → new Athena table (`<dataset>_annotated`) + optional Neptune enrichment edges.
- **Benchmarkable?** Treat as a *capability showcase*, not a scored benchmark item.
- **IAM:** HealthOmics run role + S3 access to the RODA source + output bucket (env-driven, no hardcoded account).

---

## Feature 3 — Human-in-the-loop context graph (self-improving hub)  → target v1.3.0
**Accelerator 1 extension · Size: Largest / most novel · Risk: high (governance, provenance, trust)**

### Scope
The user contributes **institutional knowledge the systems-of-record don't hold** — how they process oncology
data, local terminology, cohort conventions, "we treat X as actionable" — captured as a **context graph** and
used to improve the agent's answers on *their* data. Makes the hub personalized + read-write.

### Grounding (Arize "self-improving agent on a context graph", May 2026)
- Capture human **corrections/overrides** to the agent as structured traces + annotations = a context graph
  (nodes: requests/decisions/entities/precedents; edges: "agent said X citing Y; human overrode to Z citing
  precedent P"). *Institutional knowledge that lived in a person's head becomes mineable data.*
- **Mine** the disagreements for patterns → feed back as **config/instructions** (no fine-tuning).
- Measured result in their demo: **53.8% → 83.1%** agreement with the human reviewer over 4 cycles.
- Key insight for us: the context graph is a **distinct knowledge tier** from the curated graph — it carries
  *human reasons*, not system-of-record facts.

### How it maps to the semantic hub
- **Storage:** structured domain context → new graph nodes (`:UserContext` / `:Annotation` / `:Precedent`
  linked to genes/diseases/workflows); conversational preferences → **AgentCore Memory** (semantic strategy).
  Likely both.
- **Provenance (critical):** user-contributed facts get a distinct tag `[UserContext]` — a user assertion ≠
  PrimeKG authority. The provenance-faithfulness model (Accelerator 2) must add this tier and NOT treat it as
  fabrication when the layer legitimately holds user context.
- **Correction vs augmentation:** fixing the hub (e.g., a wrong MONDO mapping) vs adding preference/terminology
  — different mechanisms; support both.
- **Self-improving loop (ties to Accelerator 2):** capture user corrections → mine → feed back → **measure
  correctness lift on the user's questions** using our benchmark framework. This closes Accelerator 1 ↔ 2.

### Open design questions
- Capture UX: conversational ("remember that we…") vs structured form vs document upload?
- Conflict resolution when user context contradicts the curated graph.
- Scoping/security: per-user vs per-org isolation + governance.
- Do we mine/cluster overrides (Arize-style) or store verbatim user assertions? (start verbatim + tagged)

---

## Accelerator 2 addition — validate an EXTERNAL dataset (LAB-Bench DbQA2)  → target v1.2.0
**Proves the benchmark framework is domain/dataset-agnostic (not just our 84 oncology Qs).**

- **Source:** LAB-Bench (`lab-bench.pdf` at repo root); the **DbQA** subtask (database QA over biology
  databases). `evaluation/filter_dbqa2.py` already filters DbQA2 → `golden_dataset_tier1.json` (gated content,
  gitignored — do NOT commit the ideal answers / canary strings).
- **Goal:** run OUR framework (tier ladder + 3-dimension scoring + reproducibility) on DbQA2 questions to show
  the methodology generalizes to a published external benchmark, and to sanity-check our scorers against a
  third-party gold standard.
- **Open question:** DbQA2 answers are held-out/gated — how do we report results without leaking GT? (aggregate
  metrics only; keep the dataset gitignored.)

---

## Proposed sequencing & versioning
| Version | Contents |
|---|---|
| **v1.0.0** (now) | Two accelerators, oncology reference, de-accounted, tested — **check-in baseline** |
| **v1.1.0** | Feature 1 (radar chart) — quick win |
| **v1.2.0** | Feature 2 (HealthOmics 1000-Genomes VEP showcase) + Accelerator-2 DbQA2 external validation |
| **v1.3.0** | Feature 3 (human-in-the-loop context graph) — the novel, self-improving-hub capability |

**Cross-cutting pillar:** Features 2 & 3 both move the hub from read-only retrieval to **action + read-write**,
introducing a shared need for a **human approval / feedback gate** and **user-provenance tagging**. Design that
foundation once and reuse it across both.
