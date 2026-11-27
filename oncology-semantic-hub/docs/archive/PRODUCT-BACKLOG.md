# Oncology Semantic Hub — Product Backlog

> **Purpose:** single source of truth for outstanding work.
> **Last updated:** 2026-07-20 (reconciled against the deployed system + slides `oncology_semantic_hub_v12.pptx`).
> **Objective:** show oncology teams how to build **research agents on data they trust and that is relevant
> to their science.** Priorities below are grouped by the pillars that serve it — **Trust**, **Relevance**,
> **Enablement ("how to build")**, and **Demo quality**. See `PROJECT-STATUS.md` for current state.

> ⚠️ The previous version of this file (June 1) was badly stale (said N=12 questions, agents local-only,
> PubMed "not started"). This rewrite reflects reality: 63-Q deployed benchmark, AgentCore Runtime,
> OLS + hybrid search + cBioPortal + provenance all shipped.

---

## Recently completed (reconciled 2026-07-20)
- ✅ **Deployed L1/L3 on AgentCore Runtime** + native evaluators (Correctness 0.968 · Faithfulness 1.0 ·
  Trajectory 1.0). *(retires old P0.1/P0.2)*
- ✅ **63-question golden benchmark** (template-driven, programmatic GT): **L1 50.8% → L3 98.4%** correctness,
  **95.2%** reproducibility. *(retires old P0.4 statistical-power, N=12)*
- ✅ **OLS ontology layer** (old P1.4) — authoritative CURIEs; fixes cross-system misalignment.
- ✅ **Hybrid / literature search** (old P1.1) — a **Bedrock Knowledge Base on S3 Vectors + Titan v2**
  (`knowledge_search` tool): recall → OLS → graph/SQL → **cited** evidence, verified **no fabricated citations**.
- ✅ **cBioPortal multi-source lake** — copy-number (`source_cbioportal`) + expression queryable
  (fixed a Glue duplicate-partition-column defect; encoded in `scripts/07_create_athena_tables.py`);
  cross-source id reconciliation (`gbm_tcga`=`TCGA-GBM`).
- ✅ **Answer-level provenance** — inline `[KB PMID]`/`[Graph]`/`[Lake]`/`[OLS]` tags + "Sources & provenance".
- ✅ **Cross-system ontology misalignment** spotlight (TCGA-LGG → `MONDO:0021637`).
- ✅ **DLA accelerators + BYOD** — Metadata-Builder + Context Weaver + OLS overlay; L3-accel 90.5% (full 63).
- ✅ **Compare UI** with L0 · L1 · L3 and per-layer memory.

---

## P0 — Credibility of the proof (TRUST) + a clean showcase

### P0.1 — Re-baseline the 63-Q eval on **Sonnet 4.5** (+ adopt the comparison-design)
**Why:** the headline **50.8% / 98.4%** (and slide 18) were on **Sonnet 4** (deprecated); deployed agents now
run **Sonnet 4.5**. Also adopt `comparison-design.md`: the numbers must reflect the reframed ladder.
**Do:** (a) **redefine L1** = lake **+ raw external tools** (Biomni gateway — already implemented); (b) add
**cross-scope questions** (need internal+external, with *ambiguous* identifiers) so raw-L1's unreliability is
measured vs L3's orchestration; (c) re-run `run_l1_l3_compare.py` + `run_agentcore_eval.py`; (d) refresh
README, slides, `BENCHMARK_REPORT_V2.md`, `validation-framework-status.md`; (e) sync `demo-golden-thread.md`
to the new L1 definition. Optional: multi-model ablation (model-independence headline).
**Effort:** ~1 day. **Depends on:** P0.3 (context traceability) landing first, per owner.

### P0.2 — Demo polish + hygiene
- Collapse the L3 **tool-narration** behind a "How L3 got this" expander in `chat_ui.py` so the
  provenance-tagged answer leads.
- **Honest L0 framing** (L0 = bare LLM; a public PubMed/web tool could also cite — L3's edge is *your*
  indexed evidence + hub fusion).
- **Delete orphaned L3 runtimes** from iterative redeploys (keep only the one in `agent_config.json`). *(destructive — confirm keep-list)*
**Effort:** ~1–2 hrs.

### P0.3 — Context traceability & confidence *(owner priority — do BEFORE the P0.1 re-baseline)*
**Why:** for "data they trust," a scientist must see **what context the hub gave the agent, from where, and
how much to trust it.** Today we tag each *answer* fact by **source system** (`[Graph]`/`[Lake]`/`[KB PMID]`/
`[OLS]`) + a "Sources & provenance" section, and native **Faithfulness** checks answer↔tool-output grounding.
**Gaps:** (a) no **record/version-level lineage** (which edge/row/passage, which source DB, which snapshot,
which query); (b) no **quantified confidence** of the provided context.
**Do:** a **context ledger / evidence card** per answer + a per-tier **confidence signal** from data we
already have — KB retrieval similarity score; **OLS exact-vs-approximate** match (the misalignment signal);
graph edge source/enrichment (ClinVar count, COSMIC tier); lake **completeness/denominator** (e.g. 371 of
617 with mutation data) + pinned snapshot; **reproducibility** across runs. Flag low-confidence context
(e.g. approximate ontology maps) explicitly; roll up to an overall grounding-confidence (High/Med/Low + why).
**Then** add a **context-traceability metric** to the validation run (P0.1).
**Effort:** ~1 day design + first implementation. **See:** `docs/context-traceability-design.md` (to author).
**Verify first:** whether PrimeKG **edges carry source/evidence** in the Neptune load (node enrichments do).

### P0.4 — Live groundedness metric in the Compare UI *(surfaces P0.3 live; design documented)*
**Why:** show a **per-question groundedness score + disposition** (RELEASE/CAVEAT/WITHHOLD/REFUSED/N-A)
**inline, with the answer**, so trust is visible during the demo — not just in offline eval.
**Do:** (P1) agent emits an **evidence bundle** `{answer, evidence[], layer}` from `invoke()`; (P2) a small
reusable **LLM-as-judge scorer** (answer vs evidence, temp 0) + disposition mapping; (P3) a **chip** in
`chat_ui.py` per column with an expandable "why"; (P4 optional) deterministic value-match, register the rubric
as an **AgentCore custom evaluator** (live↔batch parity), and flip **display→gate** (O1).
**Key nuance (measured):** L1 is Faithful 1.0 but Correct 1/7 → chip tooltip must say **"grounding, not
correctness."** L0 → **N/A** + cited-sources list (fair-to-L0).
**Recommended defaults recorded:** independent judge model · disposition-only chip (numeric on hover) ·
reusable scorer module · display-only v1.
**Effort:** ~1–2 days. **Depends on:** P0.3 evidence card. **See:** `docs/live-groundedness-ui-design.md`.
**Status:** documented plan — not started.

### P0.5 — Context Relevance + Groundedness metrics *(expose the L1<L3 context gap; plan documented)*
**Why:** AgentCore **Faithfulness** (non-contradiction) can't separate L1 from L3 (both ~1.0); Correctness
separates the *answer* but nothing measures the **quality of the retrieved/assembled context**. Motivating case:
the **Fisher's test** — L3 assembles a real multi-source contingency (relevant/sufficient) while L1 hands
thin/textbook context downstream (garbage-in), yet both are "faithful."
**Do:** add **Context relevance** (AgentCore built-in — verify `{retrieved_passages}` mapping for tool agents,
else custom judge) + a **support-based groundedness** judge (RAGAS-style "claims supported-by context", reused by
the P0.4 live chip; optional Bedrock Guardrails contextual-grounding cross-check) + a deterministic
**downstream-input adequacy** check for the co-occurrence questions. Shares the **evidence bundle** with P0.4.
**Effort:** ~1–2 days (after evidence bundle). **See:** `docs/context-relevance-groundedness-plan.md`.
**Status:** plan — not started.

---

## P1 — Measure & extend the trust/relevance story

### P1.1 — Hybrid-search / evidence evaluation
**Why:** turn "no fabricated citations / grounded recall" into a **measured** metric (TRUST).
**Do:** implement the plan in `hybrid-search-design.md` → "Validation-framework integration plan":
`evaluation/golden_hybrid.json` (~8 Q, `cited_evidence` + `negative`), `score_citations()` scorer,
`evaluation/eval_hybrid.py` (promote `agentcore/kb/hybrid_check.py`); run L3/L1/L0 to quantify L0 fabrication vs L3=0%.
**Effort:** ~1 day.

### P1.2 — **OncoKB actionability (Levels 1–4)** — *closes the "so what?" gap*
**Why:** after "EGFR has 31 drugs" (Q3/Q4), every audience asks **"is this finding clinically actionable?"**
OncoKB adds **FDA-recognized therapeutic actionability levels (L1–L4, + R1/R2 resistance)** to variants/genes
already in the hub. Fills the Oncology-Extension spec's **"Cancer Biomarker"** entity (~3,000 from CIViC/OncoKB).
**Do (small ETL, high impact):**
- Ingest OncoKB actionable variants (single API/download) → map to existing **gene/variant** nodes (Hugo symbol).
- **New graph edges:** `variant → actionability_level → drug` (today we have only `gene → drug`) — a meaningful
  schema expansion; annotate nodes with `oncokb_level`.
- Demo tie-in (new beat after Q3/Q4): *"Which of those EGFR alterations are clinically actionable, and at what OncoKB level?"*
**Caveat:** confirm **OncoKB license/API terms** for programmatic/bulk use (academic vs commercial).
**Effort:** ~1 day. **Demo value:** very high.

### P1.3 — Internal-evidence proxy in the KB
**Why:** make "your *private* evidence, not just public PubMed" tangible (RELEVANCE / BYOD).
**Do:** add a few clearly-labeled mock internal documents (study summaries / target dossiers) to the KB corpus.
**Effort:** ~1–2 hrs.

### P1.4 — Model independence + ablations *(slide 12 "Next")*
**Why:** show the hub's lift is model-agnostic and attributable to specific layers.
**Do:** run the 63-Q benchmark across 2–3 models (gap should narrow with the hub); ablate ClinVar / ontology /
patient overlay to isolate each layer's contribution.
**Effort:** ~1–2 days.

### P1.5 — SME review of ground truth
**Why:** avoid customer challenges on specific GT values (TRUST).
**Do:** SME (clinical/biomedical) review pass on `evaluation/golden_dataset.json`; flip verified flags.
**Effort:** SME time.

---

## P2 — Dataset enrichment (RELEVANCE / breadth) — from slide 17

### P2.1 — Gene/variant enrichment (same genes, deeper annotation)
- **OncoKB** — see **P1.2** (prioritized).
- **CIViC** — community-curated clinical variant interpretation (complements OncoKB).
- **PharmGKB** — drug response by genotype.
- **IntOGen** — statistical cancer-driver gene identification.

### P2.2 — New patient cohorts (different patients, same genes)
- **MSK-IMPACT** (~18K real clinical sequencing cases) · **AACR GENIE** (100K+ multi-institution) ·
  **GDC TARGET** (6,542 pediatric) · **CPTAC** (proteomics + genomics — enables the protein-abundance
  question Q5 currently refuses).

### P2.3 — Public evidence connectors (patient → disease → drug → trial)
- **ClinicalTrials.gov** (trial matching) · **OpenTargets** (target–disease evidence) · **GtoPdb** (pharmacology).
  Same KB/connector pattern as hybrid search.

### P2.4 — Single-cell / spatial (new node types)
- **CellxGene (CZI)** — higher-resolution modalities; larger effort (new entity types).

---

## P3 — Enablement & engineering

- **P3.1 — Package the "how to build" narrative** (BYOD + DLA accelerators) for an oncology audience —
  the enablement pillar of the objective. See `DLA-data-accelerators/OUTPUTS.md`.
- **P3.2 — Single-runtime, per-invocation layer selection** — collapse L1/L3 into one ARN (read `layer`
  from payload). Tradeoff: one IAM role holds the union of permissions (note if claiming a true ablation).
- **P3.3 — Provenance depth** — record/passage-level lineage beyond source-system tags.
- **P3.4 — Durable AgentCore Memory** — replace in-process warm-container memory.
- **P3.5 — Patient nodes vs metadata pointers** — revisit the architectural refactor (graph holds semantic
  relationships; raw patient data in the lake). Verify no per-patient traversal capability is lost.
- **P3.6 — Normalize legacy ClinVar/COSMIC core enrichments into the extension** — the original build stamped
  `clinvar_pathogenic_count` / `clinvar_top_significance` and `cosmic_tier` (74 CGC Tier-1 flags) as properties on
  **core** `gene_protein` nodes. Per the SDL spec these are extension-scoped (COSMIC → Oncology; germline ClinVar
  → Rare Disease), not core (core = UniProt/Ensembl/HGNC/GO/HPO/OBO). Migrate into the `ta_oncology` extension
  (COSMIC driver flag) + a rare-disease overlay (germline ClinVar), referencing core by gene ID, then drop the
  core-node properties — matching the v3 RODA extension pattern. **Blast radius:** queries + the hub skill
  reference these today (documented as a known deviation in `skills/.../references/caveats.md`). Not urgent.

---

## P4 — Methodology & governance
- **P4.1 — Process/trajectory (rubric) evaluation** for multi-hop questions (valid alternate paths).
- **P4.2 — Confidence intervals** (bootstrap) + published-benchmark baselines (LABBench2 DbQA2 if available).
- **P4.3 — Keep `PROJECT-STATUS.md` + this backlog current** (done this pass; re-check each milestone).

---

## Recommended sequence (toward a credible, relevant showcase)
**P0.3 (context traceability & confidence)** → **P0.1 (Sonnet 4.5 re-baseline + L1 redefinition + cross-scope)**
→ **P0.2 (demo polish + cleanup)** → **P1.1 (hybrid eval)** → **P1.2 (OncoKB actionability)** →
**P1.3 (internal-evidence proxy)** → then breadth (P2) + enablement (P3).

---

## Completed work log (historical)

### Sprint 1 (Apr 30, 2026) ✅
PrimeKG ingestion (129K nodes, 4M edges); TCGA patient data (11,428 cases, 33,939 samples); all 33 TCGA
cancer types with mutation data.

### Sprint 2 (May 1, 2026) ✅
ClinVar (6,286 genes); expression for all TCGA studies; graph algorithms; Strands agent + Streamlit.

### Sprint 3 (May 2026) ✅
AgentCore harness; COSMIC CGC (74 Tier-1); cross-system misalignment documented; benchmark MVP.

### Since (Jun–Jul 2026) ✅
AgentCore Runtime deploy (L1/L3) + native evals; 63-Q golden benchmark (50.8%→98.4%); OLS layer;
hybrid search (Bedrock KB); cBioPortal multi-source + LF/catalog fix; inline provenance; DLA accelerators
+ BYOD; L0 in Compare UI. See `docs/PROJECT-STATUS.md`.

---

## Reference documents
| Document | Location |
|---|---|
| Project status | `docs/PROJECT-STATUS.md` |
| Documentation index | `docs/README.md` |
| Validation status + priorities | `docs/validation-framework-status.md` |
| Hybrid search design + eval plan | `docs/hybrid-search-design.md` |
| Demo thread | `docs/demo-golden-thread.md` |
| Benchmark report | `docs/BENCHMARK_REPORT_V2.md` |
| Accelerator reuse manifest | `DLA-data-accelerators/OUTPUTS.md` |
| Latest slides | `oncology_semantic_hub_v12.pptx` |
