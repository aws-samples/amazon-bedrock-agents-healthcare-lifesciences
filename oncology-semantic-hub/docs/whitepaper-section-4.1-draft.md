# Whitepaper Section 4.1 — Omics: Genomic Variant Knowledge Graph (DRAFT, detailed)

> Draft for "Semantic Data Layers for Life Science Research" (v7). Owner: Hasan Poonawala.
> Status: **detailed draft for SME review** (Lisa McFerrin + scientist). Deliberately verbose —
> trim for the final section. All quantitative figures verified against the live deployment
> (Neptune graph `<your-graph-id>`, snapshot `2026-07`, verified 2026-07-09).

---

## 1. The use case

**Precision-oncology research questions cut across data that lives in incompatible silos.** A
translational researcher routinely asks questions such as *"For the genes most frequently mutated
in breast cancer patients, which are druggable, and what pathways do they sit in?"* Answering this
touches (a) **patient-level molecular data** (which genes are mutated, in how many patients),
(b) **curated biomedical knowledge** (which drugs target which genes; pathway membership;
disease–gene associations), and (c) **ontologies** (mapping a TCGA project code to a disease
concept, a gene symbol to a stable identifier). Today these live in separate systems (a data
warehouse, a knowledge graph, ontology services) with different identifiers, and stitching them
together is manual, slow, and error-prone.

The Oncology Semantic Hub is a **reference implementation of a semantic data layer** that unifies
these sources behind deterministic retrieval tools an AI agent can call, enabling:
- Unified natural-language querying across heterogeneous cancer data sources;
- Biomarker and drug-target discovery via graph traversal;
- Cross-system questions (patient data ↔ knowledge graph ↔ ontology) answered in one step;
- An AI-data-readiness benchmark that quantifies how much the semantic layer helps.

**Audience:** pharma/biotech R&D and AWS field teams who want a proven pattern to make *their own*
enterprise graph + data lake agent-ready (the hub is the pattern; customers bring their data).

---

## 2. Why a semantic hub

**The bottleneck for biological agents is not reasoning — it is the absence of deterministic
retrieval layers over fragmented data** (Anthropic, "Paving the way for agents in biology," 2026;
their VirBench study showed a frontier model returning 106, then 15, then 5 records for the *same*
query, and a deterministic retrieval layer raising accuracy toward 100% while eliminating run-to-run
variability and narrowing the gap between models).

Without a semantic layer, an LLM wired directly to a data lake:
- **Cannot answer relationship or ontology questions** — drug–gene, gene–pathway, disease
  hierarchies, and identifier mappings simply are not in the warehouse;
- **Hallucinates cross-source joins** — it guesses how a gene symbol or disease code in one system
  maps to another;
- **Fails silently and irreproducibly** — a flawed answer looks plausible and differs run to run,
  which is disqualifying for scientific workflows.

A semantic hub supplies the "context engine": curated relationships (knowledge graph), governed
access to high-volume data (data lake), and authoritative identifier resolution (ontology service).
Our validation quantifies the payoff by holding the model constant and toggling only this layer.

---

## 3. Key components

The hub follows the whitepaper's **Virtual Knowledge Graph** pattern — semantic relationships in a
graph, high-volume measurements in a lake, an agent bridging them — in three layers:

**Layer 1 — Knowledge graph backbone (relationships).** Amazon Neptune Analytics hosting **PrimeKG**
(Harvard; integrates ~20 curated resources — MONDO, DrugBank, Reactome, Gene Ontology, HPO, STRING,
DisGeNET, UBERON, and others). Node types: gene/protein, disease, drug, pathway, biological process,
molecular function, cellular component, anatomy, phenotype, exposure. Edge types include
drug↔protein, disease↔protein, protein↔protein, pathway↔protein, indication/contraindication.

**Layer 2 — Patient data lake (measurements).** TCGA data stored as Parquet on S3 and queried
through Athena: somatic mutations (all 33 TCGA projects) sourced from the **NCI Genomic Data Commons
(GDC)**, and gene expression (mRNA z-scores) + copy-number alterations sourced from **cBioPortal**.
TCGA **case** and **sample** nodes are also linked into the graph (via `case_has_diagnosis` → MONDO
disease, `sample_from_case`), so patient → disease → gene → drug traversals stay within the graph
while raw molecular volume stays in the lake.

**Layer 3 — Ontology enrichments + resolution service.** Gene nodes enriched with ClinVar
pathogenic-variant counts and COSMIC Cancer Gene Census Tier-1 flags; disease nodes enriched with
MONDO ICD-10/NCIt cross-references and definitions. Live, authoritative identifier resolution is
provided by the **EBI Ontology Lookup Service (OLS)**, deployed as an MCP server on AgentCore Runtime
and exposed to the agent as an `ontology_lookup` tool.

**Consumption — a harness-agnostic backend with multiple frontend options.** The semantic hub is
exposed through **MCP servers** — `amazon-neptune` (knowledge graph), `aws-dataprocessing` (Athena
data lake), and the deployed **OLS** MCP server (ontology resolution) — plus a **skill**
(`oncology-semantic-hub-analysis`) that is *schema-discovery-first*: it calls `get_graph_schema` /
table-metadata at runtime and composes fresh Cypher/SQL, so it adapts to a new schema without a
rewrite. Because the value lives in this **MCP + skills + semantic-layers backend**, it is
**frontend-agnostic** — teams can consume it through whichever agent harness they prefer:
- **Amazon Quick Desktop** — a no-code frontend harness (no custom agent code on the consumer side);
- **A custom agent on Amazon Bedrock AgentCore** — bring your own agent/Runtime and connect it to the same MCP servers;
- **Other MCP-capable harnesses** — Claude Code, Kiro, Codex (via platform adapters).

We support any of these; the same backend and skills serve all of them, which is what makes the hub
portable and bring-your-own-data ready.

**Validation harness.** For evaluation and benchmarking we build a **purpose-built custom agent** and
test it against the backend directly — a Strands agent driving the same semantic layers
(Neptune / Athena / OLS) through the equivalent deterministic tools (`query_knowledge_graph`,
`query_patient_data`, `get_hub_schema`, `ontology_lookup`). This gives a controlled L1-vs-L3
comparison whose results reflect the same backend any frontend (Quick Desktop or a custom AgentCore
agent) consumes.

**Cross-system correlation model** (why the hub is more than the sum of its parts):
- Patient-level: TCGA barcode links GDC ↔ cBioPortal ↔ imaging;
- Gene-level: Entrez/HGNC links PrimeKG ↔ ClinVar ↔ COSMIC;
- Disease-level: MONDO links PrimeKG diseases ↔ TCGA projects ↔ ICD-10;
- Variant-level: chr:pos:ref:alt links mutations ↔ ClinVar ↔ COSMIC.

---

## 4. Methodology (validation framework)

**Design — "attempt-and-attribute" with tier-controlled ablation.** Hold the model constant
(Claude Sonnet 4.5, temperature=0) and vary only data access/organization across an additive ladder:
- **L0 — bare LLM (no tools):** pure parametric-knowledge floor.
- **L1 — raw data lake only:** SQL over the TCGA lake (Athena) — the naive "LLM-on-the-warehouse" baseline.
- **L2 — all raw data + KB, flat organization:** lake + literature KB + flat PrimeKG (SQL self-joins) + RODA/CIViC + LLM knowledge. **No graph, no OLS.** This is a mature RAG system with all available data but no semantic layer — the real-world baseline most teams deploy today.
- **L3 — full semantic hub:** the same data organized as a semantic hub: Neptune graph traversal + OLS ontology resolution + KB + lake + RODA.

**Key design principle:** the L2→L3 delta isolates *semantic organization* value (not more data, not
a better model). Both share Claude Sonnet 4.5, temp=0, attempt-and-attribute provenance.

**2×2 Ablation (graph × OLS):** to disentangle the graph from OLS, we additionally test:
- **L3a** = graph, −OLS (hub minus ontology resolution)
- **L3b** = flat data + OLS (no graph)

This yields a 2×2 grid: L2(flat,−OLS) / L3b(flat,+OLS) / L3a(graph,−OLS) / L3(graph,+OLS).

**Attempt-and-attribute methodology:** all agents attempt every question (no forced abstention)
and attribute every fact via provenance tags (`[Lake:<table>]`, `[Graph]`, `[KB PMID:xxxxx]`,
`[OLS]`, `[PrimeKG-flat:<relation>]`, `[Model knowledge]`, `[Recalled: <source>]`). No combined
score — correctness, faithfulness, and groundedness are reported as three independent axes.

**Golden dataset — 84 questions, 12 categories, ground truth from authoritative sources:**
| Category | n | Tests | GT source |
|---|---|---|---|
| lake | 16 | SQL-answerable patient queries | pinned Athena SQL |
| graph_1hop | 10 | single-hop graph relationships | pinned Cypher |
| graph_multihop | 12 | multi-hop pathway/network traversals | pinned Cypher + manual verification |
| reconciliation | 9 | cross-system entity resolution | OLS + cross-source diff |
| ontology | 6 | ontology identifier resolution | EBI OLS4 |
| multi_source | 6 | lake + graph combined | pinned SQL + Cypher |
| actionability | 7 | CIViC somatic biomarker evidence | CIViC database |
| evidence | 2 | literature-grounded evidence | PubMed / KB |
| negative | 6 | absent-data controls | by design |
| drug_gene_relationships | 3 | drug-target queries | pinned Cypher |
| quantitative_precision | 2 | exact numeric answers | pinned SQL |
| cross_system | 2 | cross-source joins | pinned SQL + Cypher |

Questions use pure scientific/clinical language (no technical hints, no system-leaking terms).
Leakage-reviewed (79/84 clean; 5 fixed). Dataset frozen with SHA verification.

**Scoring — three independent dimensions:**
1. **Correctness** — LLM-judge (`Builtin.Correctness`, AgentCore) for the headline; custom F1 scorer
   (partial-credit for gene-list/set-valued answers) as companion.
2. **Faithfulness** — `Builtin.Faithfulness` (non-contradiction with tool outputs); plus our novel
   *provenance-faithfulness* (layer-aware attribution honesty — penalizes fabricated grounding).
3. **Reproducibility** — 5 independent runs per question per tier:
   - *Reproducibly-correct:* fraction of runs correct (≥0.8 vs GT).
   - *Self-agreement:* mean pairwise Jaccard of answer tokens across runs (correctness-agnostic).
4. **grounding_rate** (descriptor) — fraction of answer content backed by tool retrievals vs model memory.

**Novel metrics (vs borrowed):**
- *grounding_rate* — tier-discriminating (0.0→1.0 ladder); works where existing grounding checks
  (Bedrock Contextual Grounding, RAGAS faithfulness) go vacuous on tool-less agents.
- *Provenance-faithfulness (layer-aware)* — penalizes claiming a tool the layer structurally lacks.

---

## 5. SUMMARY OUTPUT OF USE CASE

### 5.1 Datasets used
| Component | Source | Role |
|---|---|---|
| Core knowledge graph | PrimeKG (Harvard Dataverse) | genes, diseases, drugs, pathways, phenotypes + relationships |
| Patient molecular data — mutations | TCGA via NCI **GDC** API (April 2026) | somatic mutations (1.83M rows), Parquet → Athena |
| Patient molecular data — expression & copy-number | TCGA via **cBioPortal** API | mRNA expression z-scores + copy-number alterations, Parquet → Athena |
| Variant annotations — ClinVar | RODA (AWS Open Data Registry) | germline + somatic significance by GRCh38 position |
| Variant annotations — CIViC | RODA | somatic clinical actionability (evidence level A–E, therapies, PMIDs) |
| Cancer drivers | COSMIC CGC (May 2026) | Tier-1 flag on 74 gene nodes |
| Disease ontology | MONDO OBO + EBI OLS | ICD-10/NCIt/definitions; live OLS resolution via MCP server |
| Literature corpus | PubMed abstracts (EGFR/GBM/resistance) + TCGA project descriptions | Bedrock Knowledge Base (hybrid search) |

Full provenance/versions/licensing: `docs/data-provenance.md`. RODA dataset catalog: `docs/roda_oncology_hub_complete_reference.md`.

### 5.2 Knowledge graph size
- **174,742 nodes · 4,095,616 edges** (Neptune Analytics, 32 m-NCU).
- Nodes: gene/protein 27,671 · disease 17,080 · drug 7,957 · pathway 2,516 · biological process
  28,642 · anatomy 14,035 · phenotype 15,311 · molecular function 11,169 · cellular component 4,176 ·
  exposure 818 · TCGA case 11,428 · tissue sample 33,939.
- Data lake: `tcga_mutations` **1,832,018** rows across 33 TCGA projects; plus expression and
  copy-number tables.
- RODA extension: `genoxus_clinvar` (ClinVar by position) + `civic_evidence` (somatic actionability).

### 5.3 Cost
- **Infrastructure ≈ $70/month:** Neptune Analytics 32 m-NCU (~$65), Athena pay-per-query
  (small data → negligible), S3 (~$0.05).
- **Validation run:** one full run = 84 questions × 4 tiers × 5 reproducibility runs ≈ 1,680 agent
  sessions — Bedrock inference (order tens of dollars per run on Claude Sonnet 4.5).

### 5.4 Headline results (84-Q, Claude Sonnet 4.5, temp=0)

| Dimension | L0 | L1 | L2 | **L3** |
|---|--|--|--|--|
| Correctness (LLM-judge) | 0.131 | 0.405 | 0.667 | **0.798** |
| Correctness (custom F1) | 0.277 | 0.528 | 0.728 | **0.834** |
| grounding_rate | 0.261 | 0.656 | 0.990 | **0.995** |
| Reproducibly-correct (5×) | 0.165 | 0.417 | 0.632 | **0.733** |
| Self-agreement (Jaccard, 5×) | 0.708 | 0.733 | 0.697 | **0.748** |
| Builtin.Faithfulness | 0.991 | 0.991 | 0.979 | 0.988 |

**The L2→L3 delta (same data, different organization):** +0.131 correctness, +0.101 reproducibly-correct,
+0.051 self-agreement. Faithfulness is ~0.99 for ALL tiers — the semantic layer's value is
**correctness + stability**, not honesty (both are honest under attempt-and-attribute).

### 5.5 2×2 Ablation — what drives the gain?
| Configuration | −OLS | +OLS |
|---|--|--|
| **Flat (PrimeKG SQL)** | L2 = 0.667 | L3b = 0.690 (+0.023) |
| **Graph (Neptune)** | L3a = 0.738 (+0.071) | L3 = **0.798** (+0.060) |

**Inference:** the knowledge **graph** is the primary driver (+0.071 over flat without OLS). OLS adds
+0.060 on top of the graph. Graph + OLS are synergistic (0.798 > 0.738 > 0.690 > 0.667), but the
graph alone gets most of the way.

### 5.6 Per-category results — where the semantic layer matters
| Category | n | L0 | L1 | L2 | **L3** |
|---|--|--|--|--|--|
| **graph_multihop** | 12 | 0.29 | 0.26 | 0.55 | **0.82** |
| **reconciliation** | 9 | 0.11 | 0.11 | 0.13 | **0.69** |
| ontology | 6 | 0.15 | 0.25 | 0.64 | **0.67** |
| multi_source | 6 | 0.40 | 0.33 | 0.45 | **0.60** |
| lake | 16 | 0.06 | 1.00 | 1.00 | 1.00 |
| graph_1hop | 10 | 0.62 | 0.44 | 1.00 | 1.00 |
| actionability | 7 | 0.68 | 0.76 | 0.91 | 0.91 |

**Interpretation:** parity on SQL-native questions (both ace them — L2 is no strawman), and a
decisive gap on **multi-hop reasoning** (+0.27) and **cross-system reconciliation** (+0.56) — the
question classes that represent real translational research work.

### 5.7 Reproducibility — where the graph stabilizes answers
| Category | n | L2 self-agreement | L3 self-agreement | gap |
|---|--|--|--|--|
| **graph_multihop** | 12 | 0.478 | **0.636** | +0.158 |
| **reconciliation** | 9 | 0.617 | **0.777** | +0.160 |
| graph_1hop | 10 | 0.780 | 0.889 | +0.109 |
| lake | 16 | 0.982 | 0.977 | −0.005 |

L3's stability advantage is concentrated on **multi-hop** and **reconciliation** — precisely the
categories where graph traversal replaces brittle flat self-joins and name-matching.

**Root cause (verified):** L2's flat name-matching fans out to disease subtypes (e.g., querying
"glioblastoma" sweeps `giant cell glioblastoma` + `astrocytoma (excluding glioblastoma)` → 166 genes
instead of the canonical 144). L3 resolves to a single MONDO node (`MONDO:0018177`) via OLS and
anchors there → stable, correct count every run. The **same mechanism** drives both the correctness
gap (166 vs 144) and the reproducibility gap (L2's interpretation flips run-to-run).

### 5.8 Example questions and answers (EGFR-GBM thread)
| Question | L0 (bare LLM) | L2 (flat data) | L3 (semantic hub) |
|---|---|---|---|
| How many distinct genes are associated with glioblastoma as a disease? | ~"500–600" `[Model knowledge]` | **166** `[PrimeKG-flat]` (inflated — sweeps subtypes) | **144** `[Graph]` ✓ (canonical MONDO anchor) |
| Is EGFR×PTEN co-occurrence in TCGA-GBM significant? Give p-value. | "p<0.001, significant" `[Model knowledge]` (**wrong**) | p≈0.28, "not significant" `[Lake]` ✓ | p≈0.28, "not significant" `[Lake]` ✓ |
| EGFR pathways → co-mutated genes in GBM cohort → druggable? | Generic textbook list | Flat self-joins (brittle) | **KB→Graph→Lake** chain with real patient counts + drug targets + PMIDs |

---

## 6. Key finding: canonical ontology anchoring eliminates the name-fan-out problem

The decisive mechanism: biomedical knowledge graphs contain multiple nodes for disease subtypes
(e.g., "glioblastoma (disease)", "giant cell glioblastoma", "classical glioblastoma"). Without
ontology resolution, a flat query matching by disease *name* sweeps all subtypes and returns
inflated, non-reproducible counts. The graph + OLS combination:
1. Resolves the query term to its **canonical MONDO identifier** via OLS;
2. Anchors the traversal on the **single canonical node** carrying that MONDO id;
3. Returns the **correct, stable** count every run.

This is not a data quality issue — the flat table *also contains* the correct 144 (under the exact
node `'glioblastoma (disease)'`). The issue is that **without canonical resolution, the LLM
inconsistently selects which name to match** → different runs hit different subtype nodes → the
count drifts (166 one run, 12,694 another). The semantic hub solves this automatically.

---

## 7. Reproducibility and reuse (accelerator)

Everything is regenerable and portable (bring-your-own-data):
- `evaluation/golden_v2.json` — 84-question benchmark (frozen, SHA-verified)
- `agentcore/semantic_hub_agent.py` — single-file env-gated agent (L0/L1/L2/L3/ablations)
- `agentcore/deploy.py` — deploy to AgentCore Runtime with layer selection
- `agentcore/run_v2_benchmark.py` — custom scorer (F1, gene-list, provenance)
- `agentcore/run_agentcore_eval.py` — native AgentCore evaluation (Builtin.Correctness + Faithfulness)
- `evaluation/provenance_faithfulness.py` — layer-aware provenance-faithfulness scorer
- `docs/benchmark-report.md` — full methodology + results reference
- `docs/roda_oncology_hub_complete_reference.md` — 28-dataset RODA catalog

Customers replace PrimeKG with their enterprise graph and TCGA with their cohort; the harness,
tools, and methodology are unchanged.

## 8. Limitations and future work
- **Single model:** results reported for Claude Sonnet 4.5 only. Multi-model validation (Llama, Nova)
  is future work; the methodology is model-agnostic.
- **Single domain:** oncology/TCGA. The framework generalizes to other disease areas with different
  knowledge graphs and patient cohorts.
- **Dataset size (84 Q):** sufficient for category-level analysis but not powered for fine-grained
  sub-category claims. Expansion planned.
- **Ground truth validated by LLM-judge + pinned queries:** expert review of golden Q&A in progress
  to establish inter-annotator agreement.
- **Temperature=0 only for main results:** temp=0.7 sensitivity tested on reproducibility subset
  (confirms the L3>L2 stability gap is temperature-invariant, ~0.20 gap).
- **Cost/latency tradeoff:** graph traversals add ~10-30s per multi-hop question vs flat SQL;
  justified by the correctness + reproducibility gain on complex queries.
- **No compute/statistics tool:** neither tier can *compute* statistics (Fisher's exact test) — both
  estimate from the contingency table. Adding a code-execution tool is future work.

## References
- Chandak, Huang, Zitnik. *Building a knowledge graph to enable precision medicine.* Sci Data (2023).
- Anthropic. *Paving the way for agents in biology* (gget-virus). (2026).
- Laurent et al. *LAB-Bench.* arXiv:2407.10362.
- Anthropic. *BioMysteryBench.* (2026).
- Chadderwala et al. *SAGE* (AWS). (2026).
- Es et al. *RAGAS: automated evaluation of retrieval-augmented generation.* (2023).
- Bailey et al. *Cell* 2018 (PMID 29625053); Sanchez-Vega et al. *Cell* 2018 (PMID 29625050);
  Liu et al. *Cell* 2018 (PMID 29625055).
- Sondka et al. *COSMIC Cancer Gene Census.* Nat Rev Cancer 2018.
- Griffith et al. *CIViC.* Nat Genet 2017.
- Vasilevsky et al. *MONDO / Monarch Initiative.*
- Cerami et al. *cBioPortal.* Cancer Discov 2012.
- NCI Genomic Data Commons; ClinVar; EBI OLS.
