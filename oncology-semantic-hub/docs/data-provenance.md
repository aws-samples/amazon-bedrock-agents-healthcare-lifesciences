# Ground-Truth Data Provenance

**Framework:** Semantic Hub Validation Framework
**Snapshot ID:** `<your-graph-id>_2026-07` (see `evaluation/config.DATA_SNAPSHOT`)
**Purpose:** Cite every source from which ground truth is derived or against which it is
cross-checked, so results in `BENCHMARK_REPORT_V2.md` and whitepaper Section 4.1 are
traceable and reproducible.

> **Temporal validity:** All answers are valid **only** for the pinned graph snapshot and
> data versions below. If the graph is mutated (nodes/edges/properties changed), ground
> truth MUST be re-verified with `evaluation/verify_ground_truth.py`.

---

## 1. Primary ground-truth sources (answers derived directly from these)

Ground truth for the core hub questions is generated **programmatically** by executing
pinned queries against the deployed data, not by any LLM. Each question stores the exact
query and the snapshot ID.

| Component | Source | Version / Access | Citation |
|---|---|---|---|
| **Core knowledge graph** | PrimeKG (Precision Medicine Knowledge Graph) | v-as-loaded into Neptune Analytics `<your-graph-id>`; Harvard Dataverse | Chandak P, Huang K, Zitnik M. *Building a knowledge graph to enable precision medicine.* Scientific Data 10, 67 (2023). https://doi.org/10.1038/s41597-023-01960-3 · https://zitniklab.hms.harvard.edu/projects/PrimeKG/ |
| **Patient data lake** | TCGA via NCI **GDC** (mutations) + **cBioPortal** (expression, copy-number) | Retrieved April 2026; Athena `oncology_semantic_hub` — Parquet partitioned by `project_id`: `tcga_mutations` (1.83M, GDC), `tcga_expression` (mRNA z-scores, cBioPortal), CNA (`source_cbioportal` 1.7M, cBioPortal; `project_id_tcga_*`). Clinical demographics (age, gender, vital_status, days_to_death, primary_diagnosis) are Neptune `:case` node properties, NOT in Athena. | Grossman RL et al. *Toward a Shared Vision for Cancer Genomic Data.* NEJM 375:1109-1112 (2016). https://gdc.cancer.gov · Cerami et al. *The cBioPortal for Cancer Genomics.* Cancer Discovery 2:401-404 (2012). https://www.cbioportal.org |
| **Variant annotations** | ClinVar | Retrieved April 2026; `clinvar_pathogenic_count`, `clinvar_top_significance` on 6,286 gene nodes | Landrum MJ et al. *ClinVar: improving access to variant interpretations and supporting evidence.* Nucleic Acids Research 46:D1062-D1067 (2018). https://www.ncbi.nlm.nih.gov/clinvar/ |
| **Cancer driver annotations** | COSMIC Cancer Gene Census (CGC) | Retrieved May 2026; `cosmic_tier` on 74 Tier-1 driver genes | Sondka Z et al. *The COSMIC Cancer Gene Census.* Nature Reviews Cancer 18:696-705 (2018). https://cancer.sanger.ac.uk/census |
| **Disease ontology enrichments** | MONDO Disease Ontology | OBO release used at load; `icd10`, `ncit`, `mondo_definition` on ~500 disease nodes | Vasilevsky NA et al. *Mondo: Unifying diseases for the world.* (Monarch Initiative). https://mondo.monarchinitiative.org |
| **Gene identifier mappings** | HGNC / NCBI (HUGO↔Entrez) | `data/mappings/hugo_to_entrez.csv` | HGNC. https://www.genenames.org · NCBI Gene. |

---

## 1a. Answer-level provenance (L3 responses)

Beyond the source citations tabulated above, the deployed **L3 agent attributes every fact in its answers
to the originating source system**, so a reader can trace each number/claim:
- **Inline source tags:** `[KB PMID:xxxxx]` / `[KB TCGA-XXX]` (knowledge-base recall), `[Graph]` (Neptune
  relationships/druggability), `[Lake: <table>]` (Athena, e.g. `tcga_mutations`, `source_cbioportal`),
  `[OLS:CURIE]` (ontology resolution).
- **"Sources & provenance" section** closes each answer, grouping knowledge base (citations) / knowledge
  graph (edges traversed) / data lake (table + filter).

Implemented in the L3 system prompt (`agentcore/semantic_hub_agent.py`). The hybrid-search knowledge base
that supplies literature citations is documented in [`hybrid-search-design.md`](hybrid-search-design.md).

---

## 2. Tier 1 — external expert-verified questions (used as-is)

| Component | Source | Version / Access | Citation |
|---|---|---|---|
| **DbQA2 public-DB questions** | LABBench2, DbQA2 task family | HuggingFace `EdisonScientific/labbench2` (gated; requires `hf auth login`); 86 items, 43 sources, all `is_opensource=False` with contamination canary | Edison Scientific / FutureHouse, LABBench2 (2026). Builds on: Laurent JM et al. *LAB-Bench: Measuring Capabilities of Language Models for Biology Research.* arXiv:2407.10362 (2024). |

Verification method for Tier 1: **expert-verified by the dataset authors**; we consume the
`ideal` answer and `answer_regex`/`validator_params` fields for deterministic scoring. We
filter to the 42 items whose source overlaps our hub/Biomni coverage (see `filter_dbqa2.py`).

---

## 3. Cross-check / validation sources (not primary GT, used to corroborate)

| Source | Role | Citation |
|---|---|---|
| **MLOmics** | Verified TCGA clinical labels + baselines to cross-check quantitative / subtype answers | Yang et al. *MLOmics: Cancer Multi-Omics Database for Machine Learning.* Scientific Data (2025). https://doi.org/10.1038/s41597-025-05235-x · arXiv:2409.02143 |
| **PrimeKG-CL** | Verified PrimeKG relationships + a KGQA task over the same graph we consume; seeds/validates graph-traversal GT | *A Continual Graph Learning Benchmark on Evolving Biomedical Knowledge Graphs.* arXiv:2605.10529 (2026). |

---

## 4. Methodology references (design, not data)

| Reference | What we adopt |
|---|---|
| Anthropic, *Paving the Way for Agents in Biology* (Jun 2026) | Core hypothesis: the bottleneck is deterministic retrieval, not reasoning; reproducibility framing. |
| BiomniBench-DA (https://huggingface.co/datasets/phylobio/BiomniBench-DA) | Process-level / trajectory evaluation for multi-hop questions (future work). |
| BioMysteryBench (Anthropic) | Grade final answers against data-derived ground truth; multi-run reliability. |
| BixBench (FutureHouse / ScienceMachine) | Difficulty context for open-ended bioinformatics tasks. |
| GenoTEX (MLCB 2025) | Expert-curated gene-expression analysis tasks; trajectory-eval alignment. |

---

## 5. Verification methods per question category

| Category | Verification | Human review |
|---|---|---|
| quantitative_precision | Programmatic (pinned Athena SQL) | No |
| drug_gene_relationships | Programmatic (pinned Neptune Cypher) | No |
| ontology_resolution | Programmatic (OLS / MONDO canonical term) | No |
| cross_system | Programmatic (both queries) | Spot-check join logic |
| multi_hop_discovery | SME-authored acceptable-answer set | Yes (Lisa + scientist) |
| negative_controls | By design (answer is "cannot determine") | No |
| tier1_public_db (DbQA2) | Expert-verified by LABBench2 authors | Inherited |

---

*Every generated golden-dataset entry stores its verification query and `data_snapshot`
in metadata so this provenance is machine-traceable, not just documented here.*
