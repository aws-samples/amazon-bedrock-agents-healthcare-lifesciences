# Oncology Hub Demo (v4) — Semantic Hub Value Demonstration

**Status: CURRENT (2026-08-10).** Aligned to the *attempt-and-attribute* methodology and the 84-Q
benchmark results. Full methodology and results: `benchmark-report.md`.

> ⚠️ **Research use only — not medical advice.** This demo runs on public, de-identified TCGA data
> for research and demonstration purposes. The drug names, clinical evidence levels (e.g. "Level B,
> PMIDs"), and treatment-implication language shown below are AI-generated outputs from a research
> accelerator — they are **not** clinical decision support, must not be used for clinical diagnosis,
> treatment, or patient-care decisions, and require qualified oncologist/clinical review before
> informing any such decision. See the top-level README's Known Limitations section.

---

## Thesis

Holding **data constant** and varying only the **organization** (flat tables vs knowledge graph +
ontology), the semantic hub makes an LLM agent more correct, more reproducible, and more grounded
on complex oncology questions — with no loss in faithfulness.

## Demo structure

The demo uses **4 questions, all on the EGFR-GBM thread**, comparing different tier pairs depending
on what each question demonstrates:

- **Q1–Q2 (L2 vs L3):** correctness + reproducibility — isolates the value of *semantic organization*
  over the same raw data. L2 is the strong baseline (same data, flat); L3 is the semantic hub.
- **Q3–Q4 (L0 vs L3):** groundedness + multi-hop orchestration — isolates the value of *data grounding*
  over pure parametric knowledge. L0 is the bare LLM (no tools); L3 is the full hub.

## Layer definitions (for this demo)

| Layer | What it has | Role |
|---|---|---|
| **L0** | No tools — pure LLM parametric knowledge | "What happens without any data?" |
| **L2** | Lake + KB + flat PrimeKG (SQL) + RODA/CIViC. **No graph, no OLS.** | "What happens with all the data but flat organization?" |
| **L3** | Same data as L2 + Neptune **graph** + **OLS** ontology | "What happens with semantic organization?" |

All use **Claude Sonnet 4.5, temperature=0, attempt-and-attribute** (no forced abstention; all
attempt and tag provenance).

---

## ★ The questions (4 core + 1 full-hub extension)

| # | Pillar | Comparison | Question |
|---|---|---|---|
| Q1 | **Correctness** | L2 vs L3 | *"In our TCGA-GBM cohort, how many distinct genes are mutated? And separately, how many genes are known to be associated with glioblastoma as a disease? Give both numbers."* |
| Q2 | **Reproducibility** | L2 vs L3 | *"How many distinct genes are associated with the type of cancer studied in the TCGA-GBM cohort?"* |
| Q3 | **Groundedness** | L0 vs L3 | *"Is the co-occurrence of EGFR and PTEN mutations in TCGA-GBM statistically significant? Give the p-value."* |
| Q4 | **Multi-hop** | L0 vs L3 | *"EGFR is a key driver in glioblastoma. Which signaling pathways is EGFR part of, which OTHER genes in those pathways are also mutated in our TCGA-GBM cohort, and are any of them druggable? Cite sources."* |
| Q5 | **Full-hub + computed test** | L3 / Quick | *"In glioblastoma, are EGFR and PTEN mutations mutually exclusive or do they tend to co-occur across the TCGA-GBM patient cohort — and is that association statistically significant? Are the two genes in the same signaling pathway, and what are the treatment implications?"* |

---

## Expected results

### Q1 — Correctness (L2 vs L3)

| Part | L2 | L3 |
|---|---|---|
| (a) genes mutated in cohort | **12,694** `[Lake]` ✓ | **12,694** `[Lake]` ✓ |
| (b) genes associated with glioblastoma (disease) | **166** `[PrimeKG-flat]` ← inflated | **144** `[Graph]` ✓ canonical |

**What to narrate:** both nail part (a) — parity floor, L2 is no strawman. On part (b) they diverge:
L3 resolves to the canonical MONDO node (144 genes); L2 name-matches and sweeps subtypes (166).
See the KEY INTUITION section below.

### Q2 — Reproducibility (L2 vs L3)

Run 3–5× in Compare mode. Expected:
- **L3:** stable at **144** every run (MONDO-anchored)
- **L2:** flips between **166** (disease-association reading) and **12,694** (mutated-in-cohort reading)

**What to narrate:** same mechanism as Q1 — without canonical resolution, the LLM interprets the
ambiguous question differently each run. The semantic hub eliminates this instability.

### Q3 — Groundedness (L0 vs L3)

| | L0 | L3 |
|---|---|---|
| Answer | `p<0.001`, "significant" `[Model knowledge]` | Retrieves real 2×2 table → p≈0.28, "not significant" `[Lake]` |
| Correct? | **Wrong** (true p = 0.28) | **Correct** |
| Grounded? | No — estimated from memory | Yes — real contingency table from TCGA-GBM |

**What to narrate:** L0 confidently fabricates a p-value from training data and reaches the **wrong
scientific conclusion**. L3 retrieves the actual patient data and reaches the correct conclusion.
Both are honest about their sources (attempt-and-attribute working) — the issue is that memory
doesn't have your cohort's data.

### Q4 — Multi-hop orchestration (L0 vs L3)

| | L0 | L3 |
|---|---|---|
| Pathways | Generic textbook list (PI3K/AKT, RAS/MAPK) | Same pathways, from the graph |
| Cohort-specific? | **No** — cannot say which genes are mutated in YOUR patients | **Yes** — queries TCGA-GBM mutations |
| Druggability? | Generic ("these are known targets") | Specific drug names + counts from graph |
| Citations? | `[Model knowledge]` / `[Recalled]` | `[KB PMID:xxxxx]` + `[Graph]` + `[Lake]` |

**What to narrate:** L0 gives a textbook answer anyone could look up. L3 chains **KB (literature) →
Graph (pathway membership) → Lake (patient mutations) → Graph (druggability)** — answering
"which of those textbook pathways are actually hit in OUR patients, and what can we do about it?"
That's the semantic hub orchestration value.

### Q5 — Full-hub orchestration + computed statistic (L3 / Quick)

Exercises **all five hub components + a real computed test — but the question gives NO tool or method
hints** (no "MONDO", no "knowledge graph", no "contingency table", no "Fisher's exact"). The agent
chooses the path on its own. A representative live Quick run (2026-08-21) chained (OLS is optional —
used here to anchor the disease):

| Step | Tool | Result | Tag |
|---|---|---|---|
| Resolve disease | OLS (`ontology_lookup`) | glioblastoma → **MONDO:0018177** | `[OLS:MONDO:0018177]` |
| Gene–disease + pathway | Neptune (`query_knowledge_graph`) | EGFR & PTEN both `disease_protein`→GBM; share **PI3K/AKT** pathways | `[Graph]` ×4 |
| Cohort contingency | Athena (`query_patient_data`) | n=371 — EGFR 82, PTEN 116, both 30 | `[Lake:tcga_mutations]` ×3 |
| Statistical test | **Code Execution (Python)** | Fisher's exact → **OR 1.36, p=0.28** (not significant) | `[Compute]` ×2 |
| Actionability | Athena RODA (`query_variant_annotation`) | EGFRvIII→erlotinib/gefitinib/rindopepimut (Level B, PMIDs); PTEN expression predicts TKI response | `[RODA:civic_evidence]` ×2 |
| Caveats | — model memory | mechanism note + PTEN-CNV caveat | `[Model knowledge]` ×2 |

**Scores (representative run):** grounding_rate = **0.857** (12 tool-backed ÷ 14 tags),
provenance_faithfulness = **1.00** (0 fabricated). Exact tag counts vary with the answer/phrasing — the
principle (tool-backed ÷ all; 1 − fabricated ÷ all) is what's fixed; re-validate the scientific question in Quick.

**What to narrate:** the semantic hub gets you *to* the data and *through* the analysis in one grounded
answer — OLS anchors the disease to a canonical id, the graph supplies the biology (association + shared
pathway), the lake supplies the cohort counts, **Code Execution runs the actual Fisher's test (p=0.28, a
real number, not an estimate)**, and CIViC adds clinical actionability with PMIDs — each fact tagged by
source. A bare LLM (L0) cannot produce cohort counts or a real p-value; it would fabricate both.

**Requires a code-execution harness (Quick)** for the real `[Compute]`: a no-code agent fabricated
p=0.55/OR 0.81 for the same table (true = p=0.28/OR 1.36) — so run Q5 in Quick, where Code Execution
computes it correctly. (Deterministic enforcement is tracked as backlog #25 — Gateway interceptors.)

---

## ★ KEY INTUITION — why 144 is right and 166 is inflated (Q1/Q2)

**Verified against the live graph + flat PrimeKG (2026-08-06):**

| glioblastoma disease node | MONDO | genes |
|---|---|---|
| **glioblastoma (disease)** | **MONDO:0018177** | **144** ← canonical, correct |
| giant cell glioblastoma | *none* | 116 |
| astrocytoma (**excluding glioblastoma**) | *none* | 27 |
| classical / proneural / mesenchymal / … | *none* | 0 |

The flat **166 = 144 ∪ 116 ∪ 27 (deduplicated)** — the extra genes come from `giant cell
glioblastoma` and, tellingly, `astrocytoma (excluding glioblastoma)` (a node *definitionally not*
glioblastoma). Only `glioblastoma (disease)` carries the canonical **MONDO:0018177**.

> **Say this:** *"L2 has no ontology service, so it name-matches the flat table → sweeps subtypes →
> 166. This is exactly the failure the graph tool warns about ('a disease NAME fans out to many
> subtype nodes and gives non-reproducible counts'). The hub does canonical MONDO anchoring
> automatically and reproducibly; the flat approach requires the analyst to already know the exact
> canonical node name, and it's unstable across runs."*

**One mechanism, two pillars:** the *same* root cause (name fan-out vs canonical MONDO anchor)
drives **both** the correctness gap (166 vs 144) **and** the reproducibility gap (L2 flips
interpretation run-to-run).

**Honest caveat (pre-empt the skeptic):** the flat table *also* contains the correct 144 — under
the exact node `'glioblastoma (disease)'`. L2's error is name-matching without canonical
resolution, not bad data. Rebuttal: the hub does this **automatically and reproducibly**; the flat
path is unstable. *(The only debatable extra: `giant cell glioblastoma` (116) — clinically a GBM
variant; `astrocytoma (excluding glioblastoma)` is definitionally wrong to include.)*

---

## Recording logistics

- **App:** http://localhost:8501 (Streamlit Compare mode)
- **Q1–Q2:** toggle L2 + L3 (L0 off). For Q2, run 3–5× and point out the flip.
- **Q3–Q4:** toggle L0 + L3 (L2 off).
- **Model:** Claude Sonnet 4.5, temp=0 (displayed in sidebar)
- **Fresh sessions:** click "🔄 New conversation" between questions to avoid context memory
- **Timing:** ~8–10 min total (each question takes 30–90s per tier)

---

## Aggregate metrics (reference — shown as a slide or panel, not live)

| Metric | L0 | L1 | L2 | **L3** |
|---|--|--|--|--|
| Correctness | 0.131 | 0.405 | 0.667 | **0.798** |
| Grounding rate | 0.261 | 0.656 | 0.990 | **0.995** |
| Reproducibly-correct (5×) | 0.165 | 0.417 | 0.632 | **0.733** |
| Self-agreement (graph_multihop) | — | — | 0.478 | **0.636** |

84 questions, 12 categories. Full breakdown in `benchmark-report.md` §17.

---

## Key messages (what the audience should take away)

1. **Same data, different result:** L2 and L3 have the same underlying data — the correctness and
   reproducibility gaps come purely from how it's organized.
2. **Graph + ontology = canonical anchoring:** the MONDO mechanism eliminates name-fan-out and makes
   answers deterministic across runs.
3. **Memory ≠ data:** L0 is confident but wrong on cohort-specific questions — grounding in your
   actual data changes scientific conclusions.
4. **Multi-hop orchestration:** the hub chains KB → Graph → Lake in one answer — something neither
   a bare LLM nor flat tables can do reliably.
5. **Faithfulness is not the differentiator:** all tiers are ~0.99 faithful (they don't hallucinate
   relative to what they retrieve). The value is in **what they can retrieve and compose**.
