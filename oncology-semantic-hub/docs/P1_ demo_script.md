# Demo Storyline — Perspective 1: Making Data AI-Ready

## Premise

A pharma research team has raw cancer genomics data (patient mutations, gene expression, variant annotations) and wants to build an agent-queryable semantic hub — like the Oncology Semantic Hub — from their own data. We walk through **one accelerator per lifecycle stage** (3 of 4 — benchmarking is covered separately), using oncology terminology throughout, building toward a PrimeKG-like environment with ontologies + patient data + metadata.

---

## Stage 1 — Build Ontologies → **Ontology Builder**

**Scene:** The team has cancer-relevant entities (genes like EGFR and PTEN, diseases like glioblastoma, drugs like Osimertinib, pathways like PI3K/AKT) scattered across internal spreadsheets and publications — but no formal ontology structure connecting them.

**What the accelerator does:**
- Takes seed entities and discovers the relevant standard ontologies (MONDO for diseases, HGNC for genes, DrugBank for drugs, Reactome for pathways)
- Maps each entity to its canonical identifier: EGFR → HGNC:3236, glioblastoma → MONDO:0018177, Osimertinib → DrugBank:DB09330
- Builds the ontology structure: disease hierarchies (glioblastoma → brain tumor → neoplasm), gene-pathway memberships (EGFR → EGFR signaling, PI3K/AKT), drug-target relationships (Osimertinib → EGFR)
- Outputs a graph-loadable ontology (nodes + typed edges) ready for Neptune

**What this replaces:** Weeks of manual ontology curation by a knowledge engineer hand-mapping every entity to every standard.

**What it produces:** The foundation of what PrimeKG is — a structured ontology graph with canonical IDs and typed relationships. The customer's "PrimeKG equivalent" starts here.

**Key demo moment:** Show the Ontology Builder resolving "glioblastoma" — it finds MONDO:0018177 (not the dental anomaly that TCGA-LGG was mis-mapped to), establishes the hierarchy, and connects to the 144 associated genes. This is the same canonical anchoring that later prevents the 166-vs-144 drift in the semantic hub.

---

## Stage 2 — Onboard Datasets → **Cancer Genomics Data Starter**

**Scene:** The team has raw patient data — somatic mutations as MAF files, expression matrices, copy-number calls — sitting in S3, but it's not queryable or linked to the ontology graph.

**What the accelerator does:**
- Ingests raw patient data from S3 (mutations, expression, CNA)
- Transforms to partitioned Parquet (by cancer type / project ID)
- Registers in AWS Glue Data Catalog → immediately queryable via Amazon Athena SQL
- Builds the join keys between the patient data and the ontology graph:
  - Hugo gene symbols → HGNC IDs (gene-level bridge)
  - TCGA project codes → MONDO disease IDs via OLS (disease-level bridge)
  - Genomic positions → ClinVar/CIViC variant IDs (variant-level bridge)

**What this replaces:** Custom ETL scripts per data source, manual ID mapping tables, and the "how do we connect the lake to the graph?" puzzle.

**What it produces:** The patient data lake equivalent of TCGA + cBioPortal in the Oncology Semantic Hub — queryable, partitioned, and linked to the ontology graph via canonical identifiers.

**Key demo moment:** Show the join-key resolution: a TCGA mutation record with `hugo_symbol='EGFR'` and `project_id='TCGA-GBM'` is linked to HGNC gene node EGFR in the graph AND to MONDO:0018177 (glioblastoma) — so a graph traversal from the disease through the gene to the drug now connects to the patient's actual mutation count in the lake.

---

## Stage 3 — Manage Context → **Metadata Curation (Context Ops Engine)**

**Scene:** The ontology graph and patient lake exist, but an AI agent doesn't know what's in them. There's no schema documentation, no data dictionary, no description of what each table or node type means. The agent can't compose queries without this context.

**What the accelerator does:**
- Introspects the live Glue catalog (table schemas, column types, partitions) + Neptune graph schema (node labels, edge types, property keys)
- Auto-generates a data dictionary: business metadata ("tcga_mutations contains somatic variants from 33 TCGA cancer types"), column-level descriptions ("hugo_symbol: HGNC gene symbol of the mutated gene"), data quality rules
- Creates a summary graph — a high-level map of what entity types exist, how they connect, and what each table contains
- Human-in-the-loop review: a domain expert approves, corrects, or enriches the auto-generated metadata before it's published to the agent

**What this replaces:** Hand-written `get_hub_schema` documentation and the tribal knowledge of "what's in the graph" that only the builder knows.

**What it produces:** The "context" that makes the semantic hub agent-consumable. In the Oncology Semantic Hub, the schema-discovery-first skill calls this metadata at runtime to compose queries — this accelerator is what generates that metadata automatically.

**Key demo moment:** Show the Context Ops Engine producing the data dictionary for `tcga_mutations` — column descriptions, join keys, example values — then a domain expert correcting one description ("consequence_type" → "VEP-predicted variant consequence, e.g., missense_variant, stop_gained") and approving it. The agent immediately uses the corrected metadata to compose a more precise query.

---

## The Arc (what we built)

| Stage | Accelerator | Input | Output | Oncology Hub Equivalent |
|---|---|---|---|---|
| 1. Build Ontologies | Ontology Builder | Seed entities | Canonical ontology graph | PrimeKG structure (129K nodes, 4M edges) |
| 2. Onboard Datasets | Cancer Genomics Starter | Raw patient files (S3) | Partitioned lake + join keys | TCGA + cBioPortal in Athena |
| 3. Manage Context | Metadata Curation | Live graph + lake | Data dictionary + summary graph | The `get_hub_schema` context layer |

**End state:** The customer has built their own semantic hub from their own data — ontology-structured, patient-data-linked, and metadata-documented. Ready for an agent to query (Perspective 2) and benchmark (covered separately).

**Transition to Perspective 2:** "Now that the data is AI-ready — ontology-structured, linked, and documented — let's see what happens when a research agent uses it to answer real oncology questions."
