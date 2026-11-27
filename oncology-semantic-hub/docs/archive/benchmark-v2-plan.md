# Oncology Semantic Hub — Benchmark v2 Plan (updated validation dataset)

> **Status:** DRAFT — iterate. **Created:** 2026-08-03.
> **Goal:** rebuild the validation dataset so the **L2-vs-L3** comparison is both **fair** (L2 fails only where a
> capability is genuinely required) and **compelling** (clear separation on multi-hop + ontology/reconciliation,
> plus the reliability story), and so the result is **publishable** (methods + findings, not a novel dataset).
> **Grounded in:** LAB-Bench (arXiv 2407.10362; DbQA2 + LitQA3 parquets), Anthropic BioMysteryBench (Apr 2026),
> Anthropic "Paving the way for agents in biology" (gget virus / deterministic context engine).

## 0. Why (thesis + current state)
- Clean 63-Q result: **L2 92.1% / 81.0% vs L3 98.4% / 95.2%** (correctness / reproducibility). After fixing the
  `glue:GetPartition` artifact, **4/6 categories are parity** → the current set is **too easy** to discriminate on
  correctness; the semantic layer's value shows only in **ontology_resolution** (+ reproducibility broadly).
- **Publishable thesis:** *holding data constant (L2 = same facts, flat; L3 = same facts, graph+ontology), the
  semantic layer's value concentrates in (a) ontology/identifier reconciliation, (b) multi-hop relationship
  traversal, and (c) **reliability/reproducibility** — not raw single-hop correctness.* This aligns with and
  extends arXiv 2606.22419 ("KG grounding helps LLMs only for out-of-training knowledge").

## 0a. Contributions (technical-report framing — the "why this matters")
1. **A genuinely apples-to-apples L2-vs-L3 comparison (L2 is given the *raw data*).** Prior KG-QA / KG-grounding
   studies (e.g. PrimeKGQA; arXiv 2606.22419) compare **no-KG vs KG**, which conflates *more data* with *better
   organization*. We uniquely give **L2 the same raw facts as L3** (flat PrimeKG + TCGA/cBioPortal lake + RODA +
   Bedrock KB literature), so the **L2→L3 delta isolates the semantic organization alone** (graph traversal +
   ontology harmonization + reconciliation). To our knowledge this data-held-constant isolation has not been done
   for an integrated biomedical hub.
2. **Method motivated by and credited to Anthropic + LAB-Bench.** Design borrows explicitly from Anthropic's
   *"agents in biology" (gget virus)* — a deterministic context engine over the **same data**, with
   **reliability/reproducibility** as a first-class metric — and *BioMysteryBench* — **objective, data-property
   ground truth**, method-agnostic grading, per-question validation, and the **5× solve-count "bimodal vs brittle"**
   reliability view; and from **LAB-Bench** — **Accuracy/Precision/Coverage** with an abstention option, structured
   JSON answers, capability/source tags, and a canary. (Credit these in the report.)
3. **Heavy oncology focus over a core biological knowledge graph.** Unlike generic/breadth science benchmarks, this
   is deep on **oncology** — TCGA/cBioPortal patient-level molecular data + CIViC/Genoxus + ClinVar/COSMIC — grounded
   on a **core biomedical KG (PrimeKG)** for biological understanding, with **cross-source ontology reconciliation**
   (TCGA↔PrimeKG↔MONDO) as a first-class axis.

## 1. Prior art to position against (must cite)
| Work | What it is | Our differentiation |
|---|---|---|
| **PrimeKGQA** (2025) | QA dataset generated from PrimeKG (graph-only) | We add patient-level **lake (TCGA/cBioPortal)** + **cross-system reconciliation** + the **L2/L3 data-held-constant** ablation |
| **arXiv 2606.22419** | Controlled study: KG grounding over PrimeKG barely moves MedQA | We isolate *organization* (L2 vs L3, same data) + measure **reproducibility**, not just accuracy; **DEEP-READ before writeup** |
| **PrimeKG-CL** (2605.10529) | Continual-learning on evolving PrimeKG (ontology drift) | Different axis; overlaps our ontology-misalignment theme |
| **MedReason / BioASQ / MedQA** | KG-path / model-knowledge QA | Model-capability benchmarks, not data-infrastructure / semantic-layer value |

> **De-prioritized:** arXiv 2606.22419 (weak affiliations; premise that KG grounding doesn't help is dubious —
> KG grounding *should* help an agent reach the right context faster). Not used as a framing anchor.

### 1a. PrimeKGQA — reuse assessment (downloaded locally 2026-08-03)
Source: GitHub `xixi019/primeKGQG` (Yan et al., ECAI 2024); dataset on Zenodo (rec 13348627 `final_*`, rec 13829395
`*_call_bioLLM`). Downloaded **`~/Downloads/primeKGQG/dataset/final_test.json`** (134 MB, **17,074 items**) for review.
- **Structure:** each item = `type` (network-motif, e.g. `1_v2`, `7_no_duplicate` = 2–4-node subgraph shape),
  `value` (subgraph triples, URL-encoded relations like `associated%20with`, `expression%20present`), `sparql`
  (query vs the PrimeKG SPARQL endpoint, node URIs `.../node/<id>`), `answer_sparql`/`answer_`. The **NL question**
  is not in `final_*` (it's produced from the `*_call_bioLLM` files).
- **Reuse verdict — DO NOT reuse questions directly:** (a) entities are random PrimeKG diseases (**not oncology** —
  e.g. "polycystic ovary syndrome", "Eruptive xanthomas"); (b) LLM-generated → semantically **noisy** (some triples
  read nonsensically); (c) SPARQL/endpoint form, not our Neptune property-graph; (d) 84k scale is generation, not
  curation. **DO reuse the *ideas*:** the **network-motif taxonomy** (2/3/4-node subgraph shapes → principled
  multi-hop templates) and their **SPARQL-validated-answer** approach (= our per-question `validation_query`). We
  instantiate motifs with **our oncology entities**, verified against **our hub**.

## 2. What we adopt from each source
### From BioMysteryBench
- **Objective-property / metadata-derived ground truth** — answers come from *controllable, verifiable properties*
  of the hub (exact counts, exact graph relationships, exact CURIEs, exact cross-source joins), never subjective
  conclusions.
- **Method-agnostic grading** — score the **final answer**, not the tool path (we already do; keep).
- **Validation "notebook" → validation query per question** ("verify, not derive"): every question ships the exact
  Cypher/SQL/OLS call that produced its GT, re-runnable to re-verify against the live hub.
- **`allowed_domains` / anti-cheat → per-layer tool restriction** (already enforced by L0/L1/L2/L3 tool gating).
- **5× solve-count reliability** — report the **bimodal-vs-brittle** distribution (solve 5/5…0/5) per layer, not
  just a mean; "brittle wins" (1–2/5) on hard questions is the reliability signal.
- **Human-solvable flag** (optional) — a small SME baseline for credibility.

### From "agents in biology" (gget virus)
- **The L2-vs-L3 design itself** = "deterministic context engine over the *same data*" — the apples-to-apples we built.
- **Reliability/reproducibility is the headline** (their 266→106/15/5 rerun collapse); lead with it.
- **"The right layer makes model choice matter less"** — optional multi-model ablation to show the hub narrows the gap.

### From LAB-Bench (DbQA2 + LitQA3)
- **Structured JSON `ideal`** → field-level deterministic scoring (e.g. `{"top_gene":"X","drug_count":N,"drugs":[...]}`).
- **`sources` → `requires` capability tag** (the key strategic addition; see §3).
- **`answer_regex` / `validator_params`** for robust extraction.
- **`key_passage`** — store the supporting evidence sentence for literature/KB questions (citation-faithfulness check).
- **`canary` string** — leakage hygiene on our dataset.
- **`mode` {file, retrieve, inject}** — track how context is supplied.
- **Accuracy / Precision / Coverage + an explicit "cannot determine from my tools" option** → selective accuracy, so
  L2 abstaining on ontology reads as honest low-coverage, not wrong.

## 3. Dataset schema (v2) — additions to `evaluation/golden_dataset.json`
Per question, add:
- **`requires`** (capability tag; the reporting axis): `lake | graph_1hop | graph_multihop | ontology |
  reconciliation | literature | multi_source`.
- **`hops`** (int) and **`min_layer`** (the lowest layer that *should* answer it: L1/L2/L3).
- **`ideal`** structured JSON GT (multi-field where applicable) + optional **`answer_regex`**.
- **`validation_query`** — exact Cypher/SQL/OLS that yields the GT (re-runnable).
- **`key_passage`** (literature/KB questions only).
- **`allow_insufficient`** (bool) — is "cannot determine" an acceptable/expected answer for lower layers.
- **`canary`** (dataset-level constant).

## 4. Question mix (target ~90–100 total: keep 63 + ~30 new hard)
| `requires` | Purpose | ~N | Expected L2 vs L3 |
|---|---|---|---|
| lake / quantitative | parity controls | 20 (existing) | parity |
| graph_1hop | parity controls (flat SQL = graph) | 10 (existing) | parity |
| **graph_multihop** (3–4 hops) | **NEW** — traversal where flat self-joins are brittle | **~12** | **L3 ≫ L2** (esp. reproducibility) |
| **ontology / reconciliation** | **NEW** — OLS-only + synonym/xref/approx-map | **~12** | **L3 ≫ L2** (correctness) |
| multi_source | lake × graph × ontology fusion | ~6 | L3 > L2 |
| negative_controls | honest refusal | 5 (existing) | parity |

Multi-hop templates (method-agnostic, single ground truth, each with a validation query):
- "Among genes in EGFR's pathway(s), which has the most `drug_protein` edges; what disease is it linked to?"
- "For the top-N GBM-mutated genes (lake), which is targeted by the most drugs (graph), and at what CIViC evidence level (RODA)?"
- "Drugs indicated for diseases associated with genes co-mutated with EGFR in GBM — resolve disease to MONDO."
- Ontology/reconciliation: synonym → canonical MONDO; TCGA project → exact-vs-approximate MONDO; ICD-10/SNOMED xref.

## 5. Metrics & reporting
- **Correctness** (deterministic + LLM-judge for negatives/abstention) — report **by `requires`** and overall.
- **Reproducibility**: bump hard set to **5×**; report **solve-count distribution** (bimodal vs brittle) per layer.
- **Precision / Coverage** (LAB-Bench) via the "insufficient information" option — selective accuracy per layer.
- **Faithfulness** (native AgentCore, `run_agentcore_eval.py`) — expected ~flat L2≈L3; report to show "faithful≠correct."
- Harness: extend `run_l1_l3_compare.py` (already `--layers`) to emit per-`requires` breakdown + solve-count buckets.

## 6. Phased execution (iterate here)
- [ ] **P0 — Positioning:** deep-read arXiv 2606.22419; write a 1-para differentiation delta. (De-risks novelty.)
- [ ] **P1 — Schema + retro-tag:** add the v2 fields; tag all existing 63 with `requires`/`hops`/`min_layer`;
      backfill `validation_query` for a sample. (Small, reversible.)
- [ ] **P2 — Author hard questions:** ~5 `graph_multihop` + ~5 `ontology/reconciliation` FIRST (with validation
      queries + structured GT) → review sample → then scale to ~24 new.
- [ ] **P3 — Harness upgrades:** per-`requires` reporting, 5× solve-count buckets, precision/coverage + abstention.
- [ ] **P4 — Re-run L2-vs-L3** on the augmented set; produce the by-capability table + reliability plot.
- [ ] **P5 — (Optional) SME/human baseline** on ~15 questions; **P6 — writeup** (methods + findings + positioning).

## 7. Open decisions (discuss)
1. Total size target (~90 vs ~110)? Keep all 63 or prune redundant quant/1-hop?
2. Include an **L1** column in the paper, or **L2-vs-L3 only** (cleanest data-held-constant story)?
3. MCQ variant (for Precision/Coverage rigor + distractors) vs stay open-response (harder GT but no guessing)?
4. Human/SME baseline in scope for v1, or defer?
5. Public release (HF dataset + canary) or internal-only technical report first?

## 8. Reusable artifacts to build
- `evaluation/golden_dataset.json` v2 (tagged + validation queries).
- A small `evaluation/validate_gt.py` that re-runs each `validation_query` against the live hub and flags drift.
- Harness additions in `agentcore/run_l1_l3_compare.py` (per-`requires` + solve-count).

## 9. Independent-review required changes (2026-08-03) — APPROVE-WITH-CHANGES
**BLOCKING (do before authoring questions — gate P2):**
1. **Bring L2's flat tools to parity FIRST.** Today "semantic layer" is confounded with tool quality (the
   `glue:GetPartition` bug swung the headline ~30pp; L2 "fumbled the flat-PrimeKG UNION and fell back to CIViC").
   Harden `query_primekg` (robust bidirectional patterns / helper), add a **standing L2 tool-health smoke test**,
   then **re-baseline** L2. This moves from a P4 follow-up to a **P1.5 prerequisite**.
2. **Dual-verify every hard-question GT on BOTH flat tables AND the graph** in `validate_gt.py`; **discard any
   question whose GT the flat data cannot reproduce** (that's a *data* gap, not a semantic-layer gap). A
   `validation_query` run only on the graph grades L3 against itself (tautological).

**REQUIRED:**
3. **Author with independent fairness/difficulty criteria BEFORE seeing L2 scores** (avoid p-hacking): every
   multi-hop question must be **expert-expressible in flat SQL**; every ontology question must use a
   **non-memorizable / obscure / approximate** mapping (not answerable from Sonnet parametric knowledge). **Freeze
   `requires`/`min_layer` tags pre-run.**
4. **Instrument failure/abstention causality in the harness:** classify each attempt as
   `tool_errored | abstained_calibrated | executed_wrong | executed_inconsistent`, and **rebuild the solve-count
   buckets on this** — so "reproducibility as headline" reflects genuine reasoning inconsistency, not flat-tool
   flakiness or tool-error abstention. Abstention due to a tool error must NOT count as calibrated "insufficient info."
5. **Add a precision penalty for list answers** (value-anchored scoring currently ignores hallucinated extras) +
   **bootstrap CIs** on the hard categories (~12 Q each is low-power).

**SECONDARY:** SME pass adjudicates **fairness** ("could L2 answer this in principle?"), not just GT correctness;
add **≥1 more model** since the reliability headline is currently model-specific (Sonnet 4.5).

*(Also fixed the §0/§1 framing inconsistency re arXiv 2606.22419 — it names the confound to control, not a result to extend.)*

## 9. Independent-review required changes (2026-08-03) — APPROVE-WITH-CHANGES
**BLOCKING (do before authoring questions — gate P2):**
1. **Bring L2's flat tools to parity FIRST.** Today "semantic layer" is confounded with tool quality (the
   `glue:GetPartition` bug swung the headline ~30pp; L2 "fumbled the flat-PrimeKG UNION and fell back to CIViC").
   Harden `query_primekg` (robust bidirectional patterns / helper), add a **standing L2 tool-health smoke test**,
   then **re-baseline** L2. Moves from a P4 follow-up to a **P1.5 prerequisite**.
2. **Dual-verify every hard-question GT on BOTH flat tables AND the graph** in `validate_gt.py`; **discard any
   question whose GT the flat data cannot reproduce** (that's a *data* gap, not a semantic-layer gap). A
   `validation_query` run only on the graph grades L3 against itself (tautological).

**REQUIRED:**
3. **Author with independent fairness/difficulty criteria BEFORE seeing L2 scores** (avoid p-hacking): every
   multi-hop question must be **expert-expressible in flat SQL**; every ontology question must use a
   **non-memorizable / obscure / approximate** mapping (not answerable from Sonnet parametric knowledge). **Freeze
   `requires`/`min_layer` tags pre-run.**
4. **Instrument failure/abstention causality in the harness:** classify each attempt as
   `tool_errored | abstained_calibrated | executed_wrong | executed_inconsistent`, and **rebuild the solve-count
   buckets on this** — so "reproducibility as headline" reflects genuine reasoning inconsistency, not flat-tool
   flakiness or tool-error abstention. Abstention due to a tool error must NOT count as calibrated "insufficient info."
5. **Add a precision penalty for list answers** (value-anchored scoring currently ignores hallucinated extras) +
   **bootstrap CIs** on the hard categories (~12 Q each is low-power).

**SECONDARY:** SME pass adjudicates **fairness** ("could L2 answer this in principle?"), not just GT correctness;
add **≥1 more model** since the reliability headline is currently model-specific (Sonnet 4.5).

*(Also fixed the §0/§1 framing re arXiv 2606.22419 — it names the confound to control, not a result to extend.)*

## 9. Independent-review required changes (2026-08-03) — APPROVE-WITH-CHANGES
**BLOCKING (do before authoring questions — gate P2):**
1. **Bring L2's flat tools to parity FIRST.** Today "semantic layer" is confounded with tool quality (the
   `glue:GetPartition` bug swung the headline ~30pp; L2 "fumbled the flat-PrimeKG UNION and fell back to CIViC").
   Harden `query_primekg` (robust bidirectional patterns / helper) + a **standing L2 tool-health smoke test**, then
   **re-baseline** L2. Moves from a P4 follow-up to a **P1.5 prerequisite**.
2. **Dual-verify every hard-question GT on BOTH flat tables AND the graph** in `validate_gt.py`; **discard any
   question whose GT the flat data cannot reproduce** (a *data* gap, not a semantic-layer gap). A graph-only
   `validation_query` grades L3 against itself (tautological).

**REQUIRED:**
3. **Author with independent fairness/difficulty criteria BEFORE seeing L2 scores** (avoid p-hacking): every
   multi-hop question must be **expert-expressible in flat SQL**; every ontology question must use a
   **non-memorizable / obscure / approximate** mapping (not answerable from Sonnet parametric knowledge). **Freeze
   `requires`/`min_layer` tags pre-run.**
4. **Instrument failure/abstention causality in the harness:** classify each attempt as
   `tool_errored | abstained_calibrated | executed_wrong | executed_inconsistent`, and rebuild solve-count buckets on
   it — so "reproducibility as headline" reflects genuine reasoning inconsistency, not flat-tool flakiness. Abstention
   due to a tool error must NOT count as calibrated "insufficient info."
5. **Precision penalty for list answers** (value-anchored scoring ignores hallucinated extras) + **bootstrap CIs** on
   the hard categories (~12 Q each is low-power).

**SECONDARY:** SME pass adjudicates **fairness** ("could L2 answer this in principle?"), not just GT; add **≥1 more
model** (the reliability headline is currently Sonnet-4.5-specific).

## 10. Design refinements from owner feedback (2026-08-03)
**On ontology fairness (supersedes review change #3b — do NOT use obscure synonyms):**
- Author ontology/reconciliation questions to **realistic TCGA-researcher needs** (canonical disease→MONDO, TCGA
  project→MONDO, common synonyms/xrefs) — not artificially obscure terms.
- **If L2 answers correctly from its own parametric knowledge, credit it as correct.** Be honest.
- **Add a groundedness / faithfulness dimension (KEY new metric).** Measure whether the answer's key claim is
  **supported by retrieved tool evidence**. Expectation: on ontology, **L2 correct-from-memory = correct but
  *ungrounded* (low groundedness); L3 via OLS = correct *and grounded* (high)**. So the semantic layer's value
  surfaces on **groundedness + reproducibility even where correctness is parity** — the honest, compelling story.
  - ⚠️ AgentCore's built-in **Faithfulness (non-contradiction) is too weak** to capture "unsupported-but-not-
    contradictory." Add a **support-based groundedness judge** (RAGAS-style: does each key claim cite a tool/source?),
    reported per `requires`. Ties to backlog **P0.5** (context-relevance/groundedness).
- Reframes the thesis: *the hub's value = **groundedness + reproducibility** (and ontology/multi-hop correctness),
  not raw single-hop correctness — and giving L2 the raw data + parametric credit makes that separation honest.*

**On multi-hop depth (confirmed):** author **3–4 hop / branching / cyclic** traversals (a 2-step lake→graph join is
already flat-SQL-expressible — see `q_cross_05`, which L2 passes). Expected L2 weakness on these = **reproducibility**
(inconsistent hop planning run-to-run), even when occasionally correct — the reliability signal.

**Correctness–reproducibility coupling (owner insight, 2026-08-03):** these are *not* independent — a brittle
multi-hop reasoner that varies its hops will also land on **wrong** answers on some runs, so L2's inconsistency
depresses **correctness too**, not just reproducibility. Measurement fix: score **correctness as the mean
solve-count over the 5 runs** (expected accuracy), not a single temp-0 run (which is a coin-flip for a brittle
model and can look falsely 100%/0%). One 5× run then yields BOTH: **mean(k/5)** = expected correctness (captures
the coupling) and the **solve-count distribution** (5/5 reliable vs 1–2/5 brittle) = reproducibility — exactly the
BioMysteryBench presentation. So on the hard multi-hop set we expect L3>L2 on **correctness *and* reproducibility**
(plus groundedness on ontology).

## 11. First sample batch + discrimination evidence (2026-08-03, autonomous)
**Authored 8 dual-verified sample questions** → `evaluation/golden_v2_samples.json` (GT verified graph==flat or via OLS4; structured JSON `ideal`). Decisions made:
- **Cohort-filtering makes multi-hop meaningful.** "Most drugs" alone surfaced promiscuous genes (CYP2C9/BCHE);
  intersecting with the TCGA-GBM cohort yields real targets (v2_multi_01 → EGFR, IDH1, PDGFRA, PIK3CA, PIK3R1, PTEN;
  v2_multihop_02 top → PDGFRA 16). Kept EGFR/GBM anchoring for the demo-adjacent ones.
- **Chose 8 (not 10)** — quality/verified over count; will broaden beyond EGFR/GBM in the next batch.

**Discrimination check (1 run each, deployed L2 vs L3)** → `evaluation/v2_discrim_results.json`:
| Question | requires | L2 | L3 | Signal |
|---|---|---|---|---|
| v2_graph1_01 | graph_1hop | ✅ grounded `[PrimeKG-flat]` | ✅ grounded `[Graph]` | parity (control) |
| v2_neg_01 | negative | ✅ abstains | ✅ abstains | parity (control) |
| v2_multi_01 | multi_source | ✅ (6 genes) | ✅ (6 genes) | parity this run (5× may split) |
| v2_onto_01 | ontology | ✅ but **ungrounded** ("general knowledge") | ✅ **`[OLS]`-grounded** | **groundedness gap** |
| v2_multihop_02 | graph_multihop | ❌ wrong top gene | ✅ PDGFRA | **correctness gap (multi-hop)** |
| v2_recon_01 | reconciliation | ❌ MONDO:0005499 (wrong, from memory) | ✅ MONDO:0021637 `[OLS]` | **correctness + groundedness** ⭐ |

**Conclusion:** the redesigned questions produce fair, multi-dimensional separation — correctness (reconciliation +
multi-hop), groundedness (ontology, correct-but-ungrounded), parity on controls. Validates the approach *with
evidence* before scaling. Note L3 also fumbled one graph query (v2_graph1_01 returned 0 then recovered) — both
layers have tool brittleness; fair to report. **Next:** wire mean-solve-count (5×) + a groundedness judge into the
harness, then scale to ~100 (broadening beyond EGFR/GBM) per §4/§6.

## 12. Authoring rule — scientific language only (owner directive 2026-08-03)
Questions must be phrased as a **researcher would ask them — pure biology/clinical language** — and must **NOT
leak implementation/technology terms**. This is both realism and fairness: the agent must map the science to
whatever tools it has, with no hint toward a data structure.
- **Ban:** "knowledge graph", "nodes/edges", relation names (`drug_protein`, `disease_protein`, `pathway_protein`),
  "data lake", "tables", "PrimeKG", "flat", "traverse", "SQL/Cypher".
- **Use:** gene/drug/disease names, "mutated in TCGA-GBM", "associated with glioblastoma", "targeted by a drug",
  "in the same biological pathway as EGFR", "MONDO identifier" (a scientific standard, allowed like ICD-10).
- Original tech-phrased version is retained per-question in a hidden `_tech_note` for our own traceability only.
- **Implication:** removing tool hints is a *stronger* test — L2 must infer how to answer without being pointed at
  the flat data. All discrimination runs must use the scientific phrasing.

## 13. Double down on KG + OLS (owner directive 2026-08-03)
L2-vs-L3 is specifically about the value of the **KG (graph traversal)** + **OLS (ontology resolution)** — the two
things only L3 has. Weight the new content to these.
- **Graph-genuinely-wins evidence:** EGFR direct interaction partners=623; within 2 steps=13,157. Flat SQL needs
  nested per-depth self-joins; **variable-depth traversal is impossible in Athena** → real capability gap (fair).
- **Constraint:** Neptune Analytics openCypher does **not** support `shortestPath`/named-path return → design around
  **reachability / N-hop neighborhood (`*1..N`)** + fixed multi-hop, not "return the path."
- **Meaningfulness rule:** pure network stats ("genes within 2 steps" = 13,157) are shallow (the PrimeKGQA trap).
  Constrain every traversal with disease/cohort/drug so it's a real research question. **Get ~3–5 real GBM/onc
  researcher questions from the owner to ground the traversal class.**
- **KG templates:** actionable targets (cohort ∩ disease ∩ druggable); EGFR interaction-partners ∩ glioblastoma ∩
  druggable; pathway→gene→drug + cohort; bounded drug↔disease mechanistic reachability; co-mutation (lake) + shared
  interaction/pathway (graph).
- **OLS templates (resolution inherent, never "what's the ID"):** disease synonym (grade IV astrocytoma→glioblastoma);
  cohort code (TCGA-GBM→disease); abbreviations (GBM, NSCLC); brand→generic drug (Tarceva→erlotinib); cross-domain
  disease naming ("breast cancer" vs "breast carcinoma"). Each embedded in a "which genes/drugs…" ask.

## 14. First v2 benchmark (65 Q, 1 run) — HONEST findings (2026-08-03, autonomous)
Results by `requires` (correctness L2→L3): lake 1.0→1.0 · graph_1hop **1.0→0.8** · graph_multihop 0.69→0.77 ·
multi_source **0.5→0.33** · ontology 0.83→0.83 · reconciliation **0.0→0.63** · negative 1.0→1.0.
**TOTAL L2 0.754 → L3 0.800. Groundedness 1.0 both.** → **NOT yet a clean L3 win.**
Root causes (diagnosed from answers):
1. **L3 graph brittleness (the #1 blocker).** For simple "drugs targeting <gene>", L3 sometimes queries the wrong
   path — the **ta_oncology `CancerBiomarker→drug` extension** or wrong direction — instead of direct
   `gene_protein-[:drug_protein]-drug`, so L3 scores *worse than L2's flat SQL* on graph_1hop/multi_source. This is
   the mirror of the earlier L2 `glue:GetPartition` bug → **must harden L3's graph-query usage FIRST (tool parity)**,
   then re-baseline. Likely the main reason L3 isn't clearly ahead.
2. **Groundedness metric not discriminating.** Synonym/brand ontology Qs are answerable from flat data after L2
   self-resolves the synonym from memory → L2's final answer is tool-grounded → no gap. The real OLS value is
   **correctness on reconciliation** (cohort→disease naming L2 can't self-resolve: L2 0.0 vs L3 0.63), not a
   groundedness delta. Tag-presence groundedness is too weak; a support-based judge would only separate where L2
   truly cannot ground.
3. **Scoring strictness:** gene-list correctness uses ≥80% coverage → near-misses score 0 for both; add
   partial-credit + a precision penalty.
**Decisions/next:** (a) harden L3 graph tool/prompt (use `drug_protein` directly for drug-target; reserve
ta_oncology for biomarker-actionability) + redeploy + test + re-baseline; (b) treat **reconciliation-correctness**
as the primary OLS signal (drop reliance on the groundedness heuristic, or replace with an LLM support-judge);
(c) refine gene-list scoring. Artifacts: `agentcore/v2_benchmark_results.json`.

## 15. Fixed-L3 re-run + paper grounding + skill decision (2026-08-03)
**After hardening L3's graph tool** (drug-target uses direct undirected `drug_protein`, not the ta_oncology
extension; new runtime `…l3_e899a088`, UI restarted on it): **TOTAL L2 0.708 → L3 0.815 (+10.7pp)** vs +4.6pp
before. Per-tag: graph_1hop 1.0/1.0 (L3 0.8→1.0 fixed), graph_multihop 0.54→0.69, ontology 0.83→1.0,
reconciliation 0.0→0.5, negative 0.83→1.0, lake 1.0/1.0. **Open anomaly:** multi_source L3 0.33 < L2 0.5 —
diagnose (L3 disease-resolution variance or strict gene-list scoring). Groundedness ~1.0 both (not discriminating;
OLS value shows as reconciliation *correctness*).
**Skill/prompt decision (owner):** system prompts are too long. Move guidance (provenance, statistical rigor,
tool-usage) into **tool docstrings** for the deployed L2/L3 agents (agent already reads them) → slim prompts; the
Quick surface already uses skills. Treat "L2/L3 skill parity with Quick" as a refactor (not mid-benchmark).
**Paper grounding (owner-provided, cite in report):** TCGA Pan-Cancer 2018 trio — Bailey (299 drivers; PMID 29625053)
→ driver-druggability/pathway; Sanchez-Vega (10 oncogenic pathways; PMID 29625050) → pathway-membership multi-hop
(= demo Beat 3); Liu (clinical/survival; PMID 29625055) → survival = **negative controls** + cohort-size lake
validation. Plus AbbVie billion-edge KG (genomically-informed subgraphs → multi_source) + Karim/OncoNet
(gene-disease assoc vs patient data). **Action:** add a **pathway-membership** question class (Sanchez-Vega's 10
pathways) + fold owner's 10–15 paper-grounded drafts into the generator (dual-verify, tech-free, structured GT).

## 16. L3 change reviewed + relocated; extension clarification (2026-08-03)
- **L3 graph-query fix INDEPENDENTLY REVIEWED** → verdict **LEGITIMATE-FIX** (removes a real L3 tool-usage bug —
  L3 was answering drug-*targeting* via the actionability extension; restores L2/L3 parity, no answer leakage).
  Per review + owner "don't bloat the prompt": **relocated the guidance from `_L3_PROMPT` into the
  `query_knowledge_graph` docstring** (removed the contradictory directed line), left a one-line pointer in the
  prompt. Redeployed L3 (`…l3_59be91a4`), regression-tested: targeting→core `drug_protein` (31 ✓), actionability→
  CIViC evidence levels ✓. UI restarted on it.
- **Extension status (clarifies "core graph + extensions"):** we DO use `ta_oncology` — for **biomarker
  actionability** (`CancerBiomarker→PREDICTS_RESPONSE_TO→drug`), NOT for plain drug-targeting (that's core
  `drug_protein`). BUT the same CIViC actionability data also sits in the flat **`civic_evidence`** table (RODA DB,
  available to BOTH L2 and L3), and L3 tends to use that flat table → the `ta_oncology` **graph** extension is
  **under-exercised**. It only differentiates on **biomarker-traversal multi-hops** → add that question class if we
  want the extension to earn its keep; else actionability is a parity control.
- **multi_source anomaly RESOLVED as a scoring artifact:** big-cohort GT gene-lists (20-40 genes) + agents return
  examples not exhaustive lists + a strict ≥0.8 binary threshold → both scored 0 though L3's *coverage* was higher.
  **Fix (pending in `run_v2_benchmark.py`):** score list questions by **coverage (partial credit)** + a precision
  penalty, not binary; or constrain list-answer GT to small sets. Coverage-based TOTAL: **L2 0.726 → L3 0.835**.
- **Prompt-slimming (owner directive):** move remaining verbose guidance (provenance, statistical rigor) from
  `_L3_PROMPT`/`_L2_PROMPT` into tool docstrings (agent already reads them); Quick surface already uses skills. Any
  further L2/L3 code change → independent review first (this one was reviewed post-hoc; process noted).

## 17. Owner's 18 paper-derived questions — verified 10 (2026-08-03)
Rephrased tech-free (per §12; originals in `_tech_note`) + verified GT against the hub → `evaluation/golden_v2_papers.json`.
Paper refs retained for provenance (Bailey/Sanchez-Vega/Liu 2018, Chandak/PrimeKG 2023, AbbVie 2022, Karim 2023).
**Verification corrected several draft guesses** (value of grounding): liu_03 → MUC16 33/33 (not TP53 27/33);
abbvie_02 → TP53 8 drugs (not EGFR — EGFR isn't in LUAD's top-10 by mutation count); bailey_03 → TCGA-LUSC 393
(not OV/UCEC); karim_01 → EGFR/NF1/PTEN (not +TP53). bailey_01 adapted to **COSMIC Tier-1** (35/74 druggable) since
we lack the external 299 list.
**Honest issues found:**
- **"most drugs / most types" → artifacts.** karim_02 (breast, most-drugged) returns CYP3A4/ABCB1/CYP2D6
  (drug-metabolism/transport genes, thousands of drug_protein edges), NOT ESR1/ERBB2; liu_03 → MUC16 (passenger).
  **Fix: filter CYP*/ABC*/SLC* (and flag passenger genes) on "most-drugs" questions** — apply to karim_02 + the
  generator's K2 template.
- **Indication-count mismatch:** hub has 18,776 indication relationships vs PrimeKG published ~5,977 — investigate
  (kg_giant storage/dedup); real data-validation finding.
- Crizotinib drug_protein includes metabolizers (CYP/ABC) + ALK/MET but not ROS1 — PrimeKG conflates target vs
  metabolism (note in the question).
**Deferred 8** (pathway-name / pan-cancer aggregation / 2-hop PPI): bailey_02, sanchezvega_02/03, liu_02,
primekg_03, abbvie_01/03, karim_03. Pathway node names discovered (PI3K: "PI3K/AKT Signaling in Cancer"; Wnt:
"Signaling by WNT in cancer"; EGFR: "Signaling by Ligand-Responsive EGFR Variants in Cancer"). Next pass.

## 18. Methodology review — SAGE (Chadderwala et al., AWS) for validating the hub + components (2026-08-03)
Read for *validation methodology* only (not their semantic-tension metric, per owner). Adoptions:
- **Component ablation is the method for "validate the components."** SAGE isolates each analysis path
  (Entity-only 43.3% / NLP-only 60.0% / Composite 63.3%) and explains where each wins. → **Add L3 component
  ablation to our harness: L3, L3−graph, L3−OLS, L3−KB (+L2), report per-`requires` marginal lift.** L2-vs-L3
  validates the whole semantic layer; ablation validates each component (the piece we were missing).
- **Grounding = traceable/reproducible/auditable** (SAGE §5.4 concept-driven vs LLM-generated) — same as our
  groundedness+reproducibility thesis; frame the headline this way (stronger than raw correctness for HCLS).
- **Per-class metrics + "where each wins"** narrative; **class-separation** view with overlap (parity) regions.
- **Honest limitations to adopt:** (a) larger dataset + **multi-annotator inter-annotator agreement (Cohen's κ)**
  in the SME pass; (b) **downstream-impact gap** — correctness/repro/groundedness are proxies; real value (does the
  hub improve research decisions) needs an SME/user study — acknowledge in the report.
- **Cite SAGE as related AWS HCLS agent-validation work**; our hub is a candidate for its future-work
  "ontology-backed registry / agentic feedback loop."

## 19. Indication-count discrepancy — RESOLVED from source (2026-08-03)
Traced from `kg_giant.csv` (the raw PrimeKG download) → hub:
- kg_giant stores **every edge BOTH directions** (confirmed for `indication`: 18,776 rows = `disease→drug` +
  `drug→disease`). **Distinct undirected pairs = 9,388.** **Neptune graph `:indication` = 9,388** (stored once).
- **Our hub truly has 9,388 indication relationships**; the earlier "18,776" was a **flat-table row-count artifact**
  (bidirectional duplication). **9,388 matches the ingested source exactly → no contamination** from the
  TCGA-linkage nodes or CIViC extension (neither adds `indication` edges). The draft's "~5,977 per PrimeKG paper"
  was an **unverified guess**; our hub is faithful to what we ingested.
- **GT rule (applies to ALL count questions):** the flat `primekg_edges` mirror double-counts every relation, so
  `count(*)` there = 2× the true undirected count. **Use the graph (undirected) count or `DISTINCT` undirected
  pairs on flat — never flat `count(*)`.** Set/DISTINCT-based GTs already correct; fixed primekg_01 → 9,388.
- **Provenance audit (owner request):** beyond the known additions (TCGA `case` linkage nodes; CIViC `ta_oncology`
  extension), core graph counts derive from kg_giant and reconcile to source. A full per-relation graph-vs-source
  reconciliation is a good validation-doc table (and a `primekg`-category benchmark question class).

## 20. Reprioritization (owner, 2026-08-03): ablation LATER
**Component ablation (L3−graph / L3−OLS / L3−KB) is deferred** — revisit once we have solid results on the current
L2-vs-L3 with the fuller (~100) question set. Near-term order: (1) consolidate golden_v2 (65 generated + 10
paper-grounded); (2) metabolism-gene filter (CYP*/ABC*/SLC*) on "most-drugs" questions; (3) fix list-question
scoring (coverage/partial-credit, not binary ≥0.8); (4) re-run L2-vs-L3 for updated results; (5) finish the 8
deferred paper questions; (6) THEN ablation.

## 21. Evidence class + groundedness=AgentCore Faithfulness (owner, 2026-08-03)
- **#3 Evidence class added (KB→graph→lake fusion, owner's key point):** both layers have KB + lake, so the
  discriminator is the **graph-relationship middle step + chaining/fusion**. Flagship `v2_evidence_01` (MET):
  KB (real corpus PMIDs 31564718/39956859 on MET) → graph (MET shares pathway + PPI with EGFR) → lake (5 TCGA-GBM
  MET-mutated patients) — fully verified. + `v2_evidence_02` (PTEN→116) and `v2_evidence_03` (PI3K/AKT/mTOR;
  citation list needs case-insensitive fix). Total dataset now 78 (`evidence:3`). Scoring: graph+lake parts have
  hard GT; KB part = cites a REAL corpus PMID (from the 60) + no fabrication.
- **#2 Groundedness = AgentCore `Builtin.Faithfulness`** (owner correction — that's our established metric, not the
  tag-heuristic in run_v2_benchmark). Plan: convert golden_v2 → AgentCore ReferenceInputs schema, run
  `run_agentcore_eval.py --config` on **L2 and L3** (native Faithfulness + Correctness over OTel traces). **Honest
  expectation:** Faithfulness (non-contradiction) will likely be ~parity/high both (as L1 0.992 vs L3 1.000 earlier)
  → validates "faithful≠correct"; it will NOT quantify the "L3 grounds where L2 answers-from-memory" advantage
  (that needs a support-based/context-relevance judge — P0.5, optional add-on).
- Order: **#2 (native Faithfulness) → #3 done → #1 (reproducibility --runs 5)**.

## 22. Component-ablation implementation plan (DEFERRED — after current numbers)
Ablation = deploy L3 variants that each drop ONE semantic component, via the existing `SEMHUB_LAYER` tool-gating.
1. Add to the layer registry in `semantic_hub_agent.py`: `L3_no_graph` (−query_knowledge_graph → isolates KG),
   `L3_no_ols` (−ontology_lookup → isolates ontology), `L3_no_kb` (−knowledge_search → isolates literature).
2. Deploy each via `deploy.py --layer <name>` (already layer-parameterized; reuse L3 LF/IAM grants); tear down after.
3. Fairness: drop the tool AND trim its prompt mention (derive tool-list section from enabled tools) — no bloat.
4. Run `run_v2_benchmark --layers L3,L3_no_graph,L3_no_ols,L3_no_kb --requires <discriminating> --runs 5`.
5. Analyze: per-`requires` marginal lift = score(L3) − score(L3−X) → component×capability contribution matrix (SAGE-style).
6. Governance: gating refactor = L2/L3 code change → independent review first; runtimes additive/reversible.
Effort ~half a day. Prereq: current L2-vs-L3 numbers (correctness + Faithfulness + reproducibility) complete.

## 23. Independent review of golden_v2 (2026-08-03) — VERDICT: REVISE
Backbone sound; **the discriminating set has GT-validity defects that would corrupt headline numbers** → fix before
trusting discriminating-category numbers. Findings (IDs):
- **Tech leaks (residual):** `q_paper_primekg_01` says "in the hub"; `q_paper_karim_02` bakes "(excluding
  drug-metabolism enzymes)" into the question; all 10 `q_paper_*` carry a **visible `verification_hint`** with raw
  Cypher/relation names → must hide (underscore-prefix) or drop from question-facing fields (§12 violation).
- **L2 fairness:** `primekg_01` (GT 9388) marks L2 wrong if it count(*)s the flat double (18,776) = storage
  artifact; `primekg_02` (Crizotinib) GT lists metabolizers as "targets" + omits ROS1 (penalizes correct L2);
  verify `v2_recon_027–032` L2 failure is naming (not tool artifact).
- **Discrimination weakness:** brand→generic ontology (`v2_onto_053–057`, Tarceva/Herceptin/Gleevec) = common
  parametric knowledge → non-discriminating; `v2_mh_045–051` are fixed ~1-hop (flat-expressible); **no
  variable-depth traversal question** (the true "impossible in Athena" gap, §13) exists; evidence Qs near-parity.
- **GT artifacts (metabolism/passenger not filtered):** `v2_mh_041` (TF/AHR), `v2_mh_042` (CYP1B1/ABCC8),
  `v2_mh_044` (NOS3/ABO), `v2_multi_036` (ABCC3/5/6/CYP26A1); `v2_mh_040` vs `karim_02` disagree (ESR2 vs ESR1);
  `v2_evidence_03` no gradeable GT; `bailey_01` ambiguous (299 vs Tier-1 74); `liu_03` MUC16 passenger; large
  entity_list GTs (`v2_mh_050` n=88, `v2_mh_048` n=59) gameable by over-listing (precision penalty still pending).
- **Coverage gaps:** `literature` tag defined but 0 literature Qs; **MONDO:0021637 cohort-misalignment (the exemplar
  clean L2-loss) is ABSENT**; no variable-depth traversal. Redundancy in templated lake Qs.
- **Schema/hygiene:** 13/78 lack canary; paper Qs use divergent schema (category/required_layers vs
  requires/min_layer/hops); tag drift (`abbvie_02` tagged graph_multihop but is multi_source).
**TOP 5 FIXES:** (1) re-derive "most-drugs" GT with an oncogene allow-list; (2) fix/drop evidence_03, correct
primekg_02 (ROS1) + bailey_01, relabel liu_03; (3) normalize schema + canary all + hide verification_hint + drop
karim_02 hint; (4) land precision/over-listing penalty before large-list Qs; (5) add MONDO:0021637 reconciliation +
≥1 variable-depth traversal; verify recon_027–032; cull memorizable brand-drug ontology items.
**Implication:** in-flight **Faithfulness is GT-independent → valid**; **correctness/reproducibility on the flagged
questions need re-scoring after GT fixes.** Parity controls + reconciliation mostly clean.

## 24. Native AgentCore Faithfulness result (2026-08-03, #2) — KEY FINDING
Ran `Builtin.Faithfulness` + `Builtin.Correctness` on BOTH L2 and L3 over the 78-Q set (pre-GT-fix).
- **Faithfulness: L2 = 0.984, L3 = 0.990 (Δ +0.006) — essentially PARITY**, both very high across every category.
- Native Correctness (LLM-judge, pre-fix GT): L2 = 0.603, L3 = 0.636 (Δ +0.034); reconciliation L2 0.00→L3 0.38
  (clean win); graph_multihop 0.25→0.12 (BOTH crushed by the metabolism-artifact "most-drugs" GT — now fixed §23).
**Interpretation (the reportable insight):** the *established* groundedness metric (Faithfulness = non-contradiction
with retrieved/tool context) **does NOT discriminate L2 from L3** — both agents are faithful to their own context
(L2 to flat data / its own knowledge; L3 to graph+OLS retrieval). This *validates* our thesis that **faithful ≠
correct**: separation must come from **verified-GT correctness + reproducibility**, not from a faithfulness score.
Faithfulness is GT-independent so this parity holds regardless of the GT fixes. **Correctness must be re-scored on
the corrected GT** (clean re-run pending). Results: `agentcore/golden_v2_agentcore_l3_eval_results.json` (L3),
`…_agentcore_eval_results.json` (L2).

## 25. Reproducibility (5x) result (2026-08-03, #1) — discriminating subset, PRE-FIX GT
Ran `run_v2_benchmark --runs 5` on the discriminating categories (reconciliation, graph_multihop, multi_source,
ontology, evidence). Mean solve-count (expected correctness over 5 runs):
- reconciliation: L2 0.00 -> L3 0.675 (clean, reproducible L3 win)
- graph_multihop: L2 0.637 -> L3 0.675 ; ontology: L2 0.833 -> L3 0.900
- multi_source: L2 0.629 -> L3 0.429 (L3 LOWER — strict binary list scoring; investigate w/ precision fix)
- TOTAL (subset): L2 0.53 -> L3 0.665 ; groundedness tag-heuristic ~0.995/1.0 (non-discriminating, known)
Caveat: this run used PRE-FIX GT (before the COSMIC-driver correction + evidence_03 drop); discriminating
correctness needs the clean re-run. Artifact: `agentcore/v2_repro5x_results.json`.
**Clean full-dataset native re-run (fixed GT, 78 Q, both layers) LAUNCHED** to finalize entire-dataset
correctness + Faithfulness on corrected GT. Faithfulness itself is GT-independent (§24) so it will hold ~parity.

## 26. multi_source L3 under-performance — diagnosis + fix; and groundedness-proof plan (2026-08-03)
**Diagnosis (from 5x per-run analysis):** small-GT multi_source (033/038/karim_01) L3 = 5/5 perfect. Large-GT
(034/035/036/037) low for TWO reasons: (1) **GT mismatch** — the large GTs are flat-computed supersets containing
promiscuous transporters/metabolizers (multi_036: ABCC3/5/6, CYP26A1; multi_037: SLC15A2/39A12) — same artifact as
"most-drugs"; L3's graph path returns a tighter/cleaner set (e.g. multi_034 consistently 11/24) → low coverage vs
bloated GT → 0 under binary >=0.8. (2) **Answer variance** — big under-bounded lists swing run-to-run (036: 12->28,
037: 4->33).
**FIX:** (A) recompute large multi_source GTs with a consistent source-agnostic definition (align "associated" =
graph disease_protein, dedupe flat double-count, strip transporter/metabolizer contamination); (B) replace binary
>=0.8 coverage with **F1/partial-credit** (precision x recall) — the pending list-scoring fix; (C) determinism for
big lists (bound the ask "top N"/"all N"; lower eval temperature). Expect L3 multi_source to rise to >= L2.
**Groundedness proof (owner-directed elevation of §22):** Faithfulness parity (0.98 vs 0.99) is INSUFFICIENT — a
faithful answer can be faithfully drawn from parametric memory (L2) OR retrieved data (L3); faithfulness can't
distinguish them. **Component ablation is the causal proof:** remove graph/OLS/KB from L3 and show correctness on
the served capability collapses to L2 level (reconciliation->L3-OLS~0; graph_multihop->L3-graph collapse) ⇒ the
correct answer is causally grounded in authoritative retrieved data, not memory. **Elevated from deferred to a CORE
experiment, sequenced right after the clean L2-vs-L3 numbers.** Complementary cheap signal: L3 emits provenance tags
("[Lake: tcga_mutations]", "[Graph]", PMIDs) → add a **provenance-attribution rate** (claims with a cited
source/path) as a direct groundedness differentiator L2-from-memory lacks. Ablation = causation; provenance = traceability.

## 27. FINAL corrected-GT metrics — entire dataset (78 Q, native AgentCore, both layers)
| category | n | Faith L2 | Faith L3 | Correct L2 | Correct L3 |
|---|--|--|--|--|--|
| lake | 19 | 1.00 | 1.00 | 0.95 | 1.00 |
| graph_1hop | 11 | 1.00 | 1.00 | 0.91 | 1.00 |
| graph_multihop | 15 | 0.95 | 0.95 | 0.33 | 0.60 |
| multi_source | 10 | 0.90 | 0.97 | 0.30 | 0.40 |
| reconciliation | 9 | 1.00 | 1.00 | 0.00 | 0.56 |
| ontology | 6 | 1.00 | 0.96 | 0.83 | 0.83 |
| negative | 6 | 0.96 | 0.92 | 0.83 | 1.00 |
| evidence | 2 | 1.00 | 0.88 | 1.00 | 0.50 |
| **TOTAL** | **78** | **0.974** | **0.974** | **0.615** | **0.769** |
**Headline: Faithfulness EXACT parity (0.974 = 0.974); Correctness L3 +15.4pp (0.615 -> 0.769).** This is the clean
proof of "faithful != correct": the semantic hub adds *correctness*, not faithfulness. L3 wins driven by
reconciliation (0.00->0.56, OLS), negatives (0.83->1.00), graph_multihop (0.33->0.60), graph_1hop/lake (->1.00).
Remaining soft spots: multi_source (0.30->0.40 — needs F1 list-scoring + GT dedupe, §26); evidence n=2 dip (small
sample). Files: `golden_v2_agentcore_l3_eval_results.json` / `…_eval_results.json` (fixed-GT run).

## 28. Component-ablation matrix (2026-08-03, #groundedness proof) — correctness by requires × layer
Stripped-L3 baseline + 3 ablations vs L2 (single run). Correctness:
| requires | L2 | L3 | L3_no_graph | L3_no_ols | L3_no_kb |
|---|--|--|--|--|--|
| graph_1hop | 1.00 | 1.00 | **0.40** | 1.00 | 1.00 |
| graph_multihop | 0.857 | 0.857 | **0.143** | 0.929 | 0.929 |
| ontology | 0.833 | 1.00 | **0.167** | 1.00 | 1.00 |
| reconciliation | 0.00 | 0.75 | **0.00** | **0.375** | 0.375 |
| multi_source | 0.75 | 0.625 | 0.50 | 0.50 | 0.50 |
| evidence | None | None | None | None | None |
| **TOTAL** | 0.717 | **0.848** | **0.239** | 0.783 | 0.783 |
**PROOF:** (1) **Graph is the load-bearing grounding component** — removing it collapses L3 0.848→0.239 (BELOW L2),
gutting graph_multihop (0.857→0.143), ontology (1.0→0.167), reconciliation (0.75→0.0), graph_1hop (1.0→0.4). The
correct answers are causally grounded in graph traversal, not parametric memory. (L3_no_graph < L2 because L3 has no
flat-primekg fallback — the graph *replaces* it.) (2) **OLS grounds reconciliation** — 0.75→0.375 (halved) when
removed; elsewhere ~no effect (ontology questions are graph-resolved, not OLS-resolved — a finding). (3) **KB effect
UNMEASURED** — evidence correctness is None (runner doesn't score evidence) so L3_no_kb looks identical to L3_no_ols;
MUST fix evidence scoring to prove KB grounding. Caveats: single run; multi_source noisy (list-scoring, §26); the
KB/evidence gap. This is the causal complement to the Faithfulness parity (§27): faithfulness can't tell memory from
data; ablation shows the correctness is *caused by* the retrieved components. Artifact: `v2_benchmark_results.json`.

## 29. Layer taxonomy refinement — additive ladder / 2×2, and phased plan (2026-08-04, owner-directed)
Reframe the comparison as an **additive value-ladder anchored on L1**, with the graph×OLS ablation expressed as a
**2×2** (KG representation × OLS). Data is held constant (same PrimeKG/TCGA/RODA/KB); only the *semantic
organization* changes across rungs.

**Layer taxonomy:**
| rung | = | semantic layer | tools (beyond shared query_patient_data / query_variant_annotation) |
|---|---|---|---|
| **L1** | lake floor | patient data only | — |
| **L2** | L1 + KB + **flat** KG | raw KG via SQL | knowledge_search, query_primekg |
| **L3a** | L1 + KB + **graph** KG | graph traversal (flat swapped out) | knowledge_search, query_knowledge_graph |
| **L3b** | L1 + KB + flat KG + OLS | flat KG + ontology | knowledge_search, query_primekg, ontology_lookup |
| **L3** | L1 + KB + graph KG + OLS | **full hub** (= deployed L3) | knowledge_search, query_knowledge_graph, ontology_lookup |

**2×2 = (flat | graph) × (±OLS) on the L1 floor.** Contrasts: graph = `L3a−L2` & `L3−L3b`; **OLS-alone = `L3b−L2`**;
OLS-on-graph = `L3−L3a`; **interaction = `(L3−L3b)−(L3a−L2)`**. Each rung uses an **appropriate, tool-matched skill
prompt built from ONE template** (parity-checked) — the prompt is held *appropriate*, NOT the variable. **Focus =
the semantic hub (data organization), not the skill addition.** Naming reuses L1/L2/L3 (L3 = full hub = deployed);
L3a/L3b are intermediate ablation cells (no "L4", no clash with prior artifacts).

**PHASING (owner-directed):**
- **Phase A (NOW):** LOCK IN **L1, L2, L3** across all THREE dimensions — **correctness + Faithfulness (native
  AgentCore) + reproducibility (5 runs)** — on the full **78-Q** set. Review/accept this matrix before proceeding.
- **Phase B (after A is accepted):** deploy **L3a** (graph, no-OLS; matched prompt — ≈ current L3_no_ols but
  re-prompted) + **L3b** (flat+OLS; NEW) as ablation cells; run the 2×2; add the **provenance-attribution** metric;
  analyze graph/OLS main effects + OLS-alone + graph×OLS interaction; decide whether this additive ladder **replaces
  the subtractive matrix (§28)**.

**Supersession:** the subtractive ablation (§28, L3−graph/−OLS/−KB) is reframed as early exploration; retain only its
"remove graph → falls **below** L2" punchline. **KB stays bundled in L2** (not isolated) by design.

**Pending metric/scoring work:** (a) fix evidence correctness (returns None — KB/evidence unscored); (b) F1 /
partial-credit list-scoring for multi_source (§26); (c) build the **provenance-attribution scorer** (Phase-B
groundedness axis — fraction of claims carrying `[Graph]`/`[Lake]`/`[OLS]`/PMID tags).

## 30. Independent design review of §29 (2026-08-04) — VERDICT: SOUND-WITH-CHANGES (GATING)
Reviewer endorsed the factorial but flagged gating issues; **do NOT run Phase A unrevised.**
1. **Prompt parity = SINGLE BIGGEST RISK.** "Appropriate per-rung prompt, held not-variable" does NOT hold — a rung
   can win on wording, and it contradicts the "isolates organization alone" claim (§0a). Same class of confound that
   swung headlines ~30pp before (glue/graph bugs §14/§16). **Must mechanically enforce:** ONE template, only an
   auto-derived tool block differs, byte-identical shared sections, published diffs, a parity unit test — OR soften
   the isolation claim. (Applies to L1/L2/L3 too — their current prompts are hand-written, not parity-controlled.)
2. **Flat→graph SWAP confound.** L2→L3a *removes* flat SQL and *adds* graph → conflates representation + query
   modality + loss of flat fallback (this is exactly why §28's L3−graph fell below L2). "Additive ladder" is a
   misnomer (graph axis is *substitutive*; only OLS is additive); "data held constant" is true at ingestion, false at
   *affordance* (variable-depth traversal impossible in flat Athena). Fix: relabel as **access-modality**; tag
   questions `needs_traversal | flat_expressible`; consider a flat+graph arm.
3. **Faithfulness framing.** Parity 0.974=0.974 is a NULL/motivation — NEVER present it as evidence L3 is "more
   grounded" (it's a tie). Ground the claim on ablation (causal) + a **support-based judge** (tag-heuristic too weak).
4. **Phasing flaw.** EVERY 2×2 contrast crosses the Phase A/B boundary → drift risk (agents/data/scorer). Locking
   Phase A also freezes KNOWN-BROKEN scoring (evidence=None, multi_source binary). Fix: **fix scoring FIRST; run all
   four cells in ONE frozen batch** (freeze data/GT/scorer/judge versions); prefer single-agent SEMHUB_LAYER gating
   over separate runtimes.
5. **Denominator traps.** §27=78Q/native, §28=53Q/coverage/1-run, §25=subset/5×/pre-fix GT are NOT comparable (L2
   0.615 vs 0.717 differs purely by set+scorer+runs). Use ONE denominator (78) / ONE scorer / ONE run-policy (5×);
   **regenerate all figures, never import** legacy numbers (esp. the §28 "below L2" punchline).
6. Interaction is **underpowered** (n=6–15/category) → bootstrap CIs; pre-register as possibly underpowered.
KB bundling in L2 = acceptable (constant across cells → cancels). Cleaner than §28 in structure (real factorial), but
the swap-confound persists and the per-rung prompt is a NEW confound surface. **Must-fixes before any run:** enforce
prompt parity (or soften claim); fix evidence + list-F1 scoring; run all cells in one frozen batch; relabel
graph axis as access-modality + tag questions; one denominator/scorer/run-policy; frame Faithfulness as null.

## 31. P0 RODA actionability class + freeze + scorer fix + Phase A launch (2026-08-04)
**RODA gap fixed:** discovered 0/78 questions exercised the RODA CIViC data. Added a **`actionability` class (7 Q,
`v2_civic_01..07`)** grounded in `oncology_semantic_hub_roda.civic_evidence` (BRAF V600E→Vemurafenib/PMID; EGFR
T790M→erlotinib *resistance*; Level-A gene count=69; EGFR-NSCLC Level-A therapies; **RODA∩TCGA-LUAD fusion**
{BRAF,EGFR,ERBB2,KRAS,MET}; TTN negative; KRAS G12C→Sotorasib). **L3-smoke-tested all 7 first (owner guardrail):**
L3 answered every one correctly, using `civic_evidence` + citing real PMIDs. RODA is now part of the questions.
**Dataset FROZEN:** 85 Q (`evaluation/golden_v2_FROZEN_phaseA.json`, sha256_16 `28fd2ac4e70028e4`; marker
`FREEZE_phaseA.json`). by_requires: lake 19 · graph_1hop 11 · reconciliation 9 · multi_source 10 · graph_multihop 15
· ontology 6 · negative 6 · evidence 2 · **actionability 7**. Canary 85/85.
**Scorer fixed** (`run_v2_benchmark.py`, harness-only — NO agent change): correctness now **continuous** (partial
credit; reproducibility = binary solve-count ≥0.8); added `expect_terms`, evidence-chain, `correct_mondo` branches;
**broadened abstention** regex (the smoke test showed L3's "no … evidence" phrasing was being missed).
**Phase A LAUNCHED (frozen 85-Q):** native Faithfulness+Correctness for **L1/L2/L3** + **reproducibility 5×** for
L1/L2/L3. All three agents READY. Decision 1 (owner): keep tier-appropriate prompts (they double as Quick skills) →
framing softened to "each tier appropriately equipped," not "pure prompt isolation." Phase B (L3a/L3b 2×2) deferred.

## 32. Catalog as an ablation component — L3c = L2 + catalog (2026-08-04, supersedes L3′)
**Decision:** drop the standalone L3′ champion-challenger; test the enriched metadata catalog as an ablation cell.
**Finding that drove it:** the "curated overlay" content (cross-system cohort-id map `gbm_tcga`↔`TCGA-GBM`, GISTIC
value semantics, data-quality caveats) ALREADY lives in L3's `get_hub_schema` + OLS — so "L3 + catalog" (L3′) was
muddy. But **L2 lacks that content**, so `L3c = L2 + catalog` gives a clean baseline where the catalog's
contribution is isolable. Prior vanilla-accelerator test (§ DLA `OUTPUTS.md`) = 90.5% vs 98.4% (parity/slightly
worse) → the auto-dictionary alone adds ~nothing; value must come from the ENRICHED layer.
**Phase C cell set — "L2 + one component" (same flat baseline):**
| cell | = | isolates |
|---|---|---|
| L1 | lake floor | — |
| L2 | +KB +flat KG | baseline |
| L3a | L2 + graph | graph traversal |
| L3b | L2 + OLS | ontology resolution |
| **L3c** | **L2 + enriched catalog** | **metadata catalog** |
| L3 | L2 + graph + OLS | full hub (champion) |
**L3c catalog = enriched** (DLA Metadata-Builder dictionary + ER-Builder join paths + our curated caveats overlay),
NOT bare Glue/auto-dictionary. Key contrasts: `L3c−L2` = catalog's marginal value; **`L3c` vs `L3a`** = "is a
cataloged flat lake competitive with the graph?" (the cheaper-alternative test). Either outcome is publishable.
Sequencing: Phase A (lock L1/L2/L3, running) → Phase B (graph×OLS ablation: L3a/L3b) → Phase C (add L3c catalog).
L3c is an agent-tooling change (catalog tool) → independent review + single-codebase discipline.

### 32a. Cell invariant (2026-08-04, owner clarification): graph = SWAP, not add
**No cell ever holds both the flat PrimeKG (`query_primekg`) AND the graph (`query_knowledge_graph`)** — two
representations of the same data would confuse the agent. So the **graph axis is substitutive** (graph cells drop
flat); **OLS and catalog are additive** (they don't duplicate a data source). Per-cell KG source / tools:
- **L1** — none.
- **L2** — flat: `knowledge_search, query_primekg`.
- **L3a** — graph (swap, NO flat): `knowledge_search, query_knowledge_graph`.
- **L3b** — flat + OLS: `knowledge_search, query_primekg, ontology_lookup`.
- **L3c** — flat + catalog: `knowledge_search, query_primekg, catalog`.
- **L3** — graph (swap, NO flat) + OLS: `knowledge_search, query_knowledge_graph, ontology_lookup`.
(All cells also share `query_patient_data` + `query_variant_annotation`.) Consequence: `L3a vs L2` = the pure
flat-vs-graph *representation* test over the same PrimeKG. Consistent with deployed agents: L3 has no
`query_primekg`; existing `L3_no_ols` = graph-only ≈ L3a (no new build). New configs needed: **L3b** (flat+OLS),
**L3c** (flat+catalog). "L2 + one component" is thus loose — read as "L2 with one semantic upgrade," graph swapped.

## 33. Faithfulness stress-test — the "forced beyond tools" class (2026-08-04, owner idea)
**Problem:** faithfulness is currently a NULL (parity ~0.97–0.99) because every question is tool-answerable. **Fix:**
add questions that FORCE an answer requiring a capability the agent lacks — the faithful response is "grounded
inputs + abstain/hand-off," the failure is fabricating a statistic/prediction from parametric memory (the demo
Fisher-test failure: L2 asserted a p-value; L3 returned the contingency table + handed off).
**Why it matters:** makes faithfulness DISCRIMINATING + rebuts "faithful by design." Expected: **L1 (no
statistical-rigor guardrail) fabricates → low; L2/L3 (hand-off guardrail) abstain → high** ⇒ faithfulness
**increases** L1<L2≈L3 (the climbing-faithfulness result, honestly).
**Archetypes (grounded inputs, withheld inference):** (1) significance/p-value (TP53×PIK3CA co-occurrence,
TCGA-BRCA); (2) mutual exclusivity (EGFR×KRAS, TCGA-LUAD); (3) hazard ratio/survival (no survival tool → must
abstain); (4) expression correlation (r,p); (5) treatment-response prediction. Faithful = grounded contingency/counts
[Lake] + "test must run in a deterministic step"; unfaithful = fabricated p/HR/r/prediction.
**Scoring:** native Builtin.Faithfulness catches fabrication (unsupported by trace) + a structured check "statistic/
prediction asserted with no compute-step provenance." **Sequencing:** SEPARATE ~5–6 Q stress-suite (do NOT reopen the
frozen 85-Q); smoke-test on L3 first + verify grounded inputs before locking; run on L1/L2/L3 same harness.

## 34. CRITICAL: multi-hop needs an AGENT fix, not just GT/scoring (2026-08-04 smoke test)
Reframed multi-hop to exact COUNTS and smoke-tested on current L3 (3 runs each): **L3 is wrong AND non-reproducible.**
- PPI-count TP53/breast (GT 116): L3 said **143** (×2) — wrong, different disease-node set.
- Pathway-count EGFR/GBM (GT 37): L3 said **37 / 31 / 28** — wrong twice, non-reproducible.
**Root cause:** L3 constructs the traversal differently each run — picks different **disease-node sets** ("glioblastoma"
vs "giant cell/classical glioblastoma"; "breast" vs "breast carcinoma"). The disease anchor is ambiguous and L3
doesn't resolve it canonically before counting. The old deterministic scorer masked this (checked only top gene).
**Reverses the earlier "GT/scoring only, no agent change" claim** — a GT/scoring fix alone will NOT fix multi-hop.
Also broad "all drivers" reframe reintroduces the metabolism artifact (CYP2C9 364, BCHE 81) → NOT usable; use
counts + canonical anchors instead.
**Fix (agent-side, flagged per governance):** guidance for L3 to **resolve the disease anchor via OLS/canonical node
FIRST, then traverse with COUNT DISTINCT** — reconciliation discipline applied inside multi-hop. Minimal tool-docstring
change (established pattern), single codebase, independently reviewed BEFORE deploy. Then GT gets canonical anchors too
(both sides unambiguous). Sequence: review → implement → redeploy L3 → smoke-test (116/37 stable) → GT/scoring fixes →
re-run full Phase A → reviewer-gate. This also explains why reconciliation is L3's clean win (it resolves) while
multi-hop wasn't (it didn't).

## 35. Multi-hop fix + Phase A.1 re-run (2026-08-04)
**Root cause (unit-tested at data layer, no redeploy):** disease-anchor ambiguity — "glioblastoma" fuzzy-matched 10
nodes, "breast" 158; the agent (and the draft GT) each picked arbitrary anchors → 143/116/88 all "correct" for
different anchors. NOT an agent-capability failure. temp=0 made it stably-wrong (consistent anchor, still fuzzy).
**Fix (two parts, both minimal):** (1) **temp=0** on the model (reproducibility lever, all layers). (2) **MONDO
anchor** — enriched canonical disease nodes with a `mondo` property (repo-owned `evaluation/disease_mondo_map.csv`,
NOT Context-Weaver-dependent) + minimal docstring/schema guidance: resolve disease via ontology_lookup → match the
single node `WHERE d.mondo=CURIE` → undirected + COUNT(DISTINCT). **Verified on deployed L3 (30ec71d9):** druggable
TP53-interactors/breast 49 = **3/3 runs**; pathway EGFR/GBM 28 = 2/3 — all runs used MONDO (vs old stably-wrong 143/37).
**Question regrounding (owner: real TCGA-paper science, not hop-tests):** mh_045–051 → "which druggable genes/proteins
in the same pathway as / interacting with X are implicated in <disease>" (Sanchez-Vega/AbbVie-style, druggable filter
bounds them); mh_039–044/karim_02 → driver-druggability (Bailey) with canonical Tier-1 anchor. **Dropped vardepth**
(contrived hop-count). RETRACTED the earlier "convert to counts" idea (unscientific) — kept "which", fixed scoring
via anchor + coverage instead.
**Phase A.1 FROZEN: 84 Q, sha256_16 7da1498245ff5d41** (`golden_v2_FROZEN_phaseA1.json`). Re-run launched: native
Faithfulness+Correctness L1/L2/L3 + reproducibility 5×, on temp=0 + anchor-guided agents. Governance: temp=0 +
docstring/schema guidance = flagged agent-config change, single codebase, reviewed direction (§34 review).

## 36. Phase C — native-MCP portability + reproducibility (deferred, owner-directed 2026-08-04)
Make the L3 fixes reproducible on ANY harness using native MCP servers (native Neptune MCP, native Athena MCP),
not just our custom agent. Scope:
- **Committed enrichment loader**: extend `scripts/15_add_mondo.py` to SET the `mondo` CURIE on disease nodes from
  the MONDO OBO (currently only sets mondo_definition/icd10/ncit) → the anchor property becomes repo-reproducible
  (today it was applied ad-hoc inline on 9 nodes — NOT reproducible by others; committed `disease_mondo_map.csv`
  is the curated subset/verification aid).
- **Mapping-as-lake-table**: load `disease_mondo_map` into the Glue catalog so a NATIVE Athena MCP (Glue-catalog
  schema discovery) can JOIN cohort/disease → canonical mondo (our custom get_hub_schema string isn't portable).
- **Anchor SKILL**: capture the resolve-disease→MONDO→anchor-single-node→undirected+DISTINCT workflow as a portable
  skill (repo skills), so native-MCP harnesses get the *discipline* (our tool-docstring guidance isn't portable).
Portable stack = data (mondo on nodes + mapping table) + skill (workflow) + native MCP tools (execute). Does NOT
affect Phase A.1 (custom agent, inline enrichment already applied). Honest caveat for the report: current state is
valid for the deployed agent but not repo-reproducible until this Phase C loader lands.

## 37. Phase A.1 RESULTS — multi-hop fix validated (2026-08-04)
Native Correctness + Faithfulness, frozen 84-Q, temp=0 + MONDO-anchor L3. **graph_multihop L2 0.29 → L3 0.86**
(was 0.27/0.27 artifact-parity — FIXED). reconciliation 0→0.78; graph_1hop 0.82→1.0.
TOTALS: Correct L1 0.357 / L2 0.655 / L3 0.833 (**L3−L2 = +17.8pp**, was +7pp). Faith 0.991/0.979/0.991 (parity).
Correctness climbs L1<L2<L3; faithfulness flat → thesis holds (hub buys correctness, not faithfulness).
Soft spots: evidence L3 0.5 (n=2, investigate); multi_source 0.40→0.50 (large-list scoring); negative L3 0.83.
Reproducibility 5× relaunched (agents free). Phase B (L3a/L3b) gating written + unit-tested (correct tool sets), NOT deployed.

---
## IDEA (owner, 2026-08-05) — L0-web baseline (LLM + web search)
Add an EXTRA tier `L0-web` = LLM + a simple web_search tool (keep pure-L0 too; L0-web is an additional curve point, not a replacement).
- Provenance: new category `[Web: url]` = GROUNDED (verifiable retrieval), DISTINCT from `[Recalled]` (unverified memory). Web citations become acceptable/faithful. Add "web" to VALID set for L0-web in provenance_faithfulness.py.
- Purpose: preempts the "why not just web-search instead of a curated hub?" objection.
- PREDICTED (to validate): web lifts PUBLIC-knowledge classes (literature/ontology/actionability/pathway) but stays ~0 on PRIVATE/structured (lake counts, graph_multihop over patient data, reconciliation, multi_source) -> hub advantage CONCENTRATES on private+structured+traversal = sharpest framing.
- REPRODUCIBILITY twist: web is non-deterministic -> L0-web likely LOWER reproducibility than the hub -> bonus headline (structured hub > web on reproducibility, not just correctness).
- IMPL (after current repro + L0 faith runs; do not disrupt): add web_search tool + SEMHUB_LAYER=L0-web gating (tools=[web_search], L0-web prompt w/ [Web]/[Model knowledge]/[Recalled] provenance) + deploy + run 84Q (correctness+provenance) + 5x repro. Modest scope, high payoff.

---
## HYPOTHESIS (owner, 2026-08-06) — OLS value is under-stressed by current ontology questions
- FINDING: current ontology Qs use COMMON synonyms — onto_053-057 = famous brand names (Tarceva/Iressa/Tagrisso/Gleevec/Herceptin), onto_052 = "grade IV astrocytoma"=GBM. L2 resolves these via KB + parametric knowledge -> L2 ontology=0.83. So we did NOT stress authoritative resolution.
- CORRECTED CLAIM: cannot say "L2 handles ontology like L3" generally — only "on common-synonym Qs". 
- HYPOTHESIS (testable): questions needing GENUINE authoritative resolution — ambiguous names mapping to multiple entities, or cross-ontology/cross-source ID reconciliation — will break L2 (flat+memory) while L3 (OLS+graph) succeeds. Sharpens L3b: predict L2 fails / L3b resolves-but-cant-join (partial) / L3 succeeds => OLS needed for hard resolution AND needs graph to pay off.
- NUANCE (respect "no obscure synonyms" rule): hardness from legitimate AMBIGUITY / cross-ontology reconciliation, NOT obscure-synonym gaming.
- TEST PLAN: add ~4-6 hard multi-ontology-resolution Qs (ambiguous/cross-source) to ontology category; run L2/L3b/L3; validate L2 fails / L3b partial / L3 succeeds. Pending go.
