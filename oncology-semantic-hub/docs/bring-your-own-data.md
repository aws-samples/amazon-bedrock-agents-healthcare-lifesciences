# Bring Your Own Data — How Customers Connect Their Own Sources

> **Purpose:** A talking-point / positioning doc (not a demo). Answers the question customers always ask: *"How do we bring our own patient data, knowledge graphs, and clinical-trial data to a solution like this?"* Companion to the demo script (`multi-source-demo-script.md`), which shows the experience on the public reference hub.

---

## The short answer

**Connecting is config-only; getting the data into the right AWS shape is a one-time step.** It is *not* "drop a file and go," but it is *not* custom integration code per source either.

**Mental model:** the customer doesn't send data to our reference hub — they **stand up their own hub in their own AWS account** (Neptune + Athena + S3), then point the *same* MCP servers and skills at it. The reference hub (`<your-graph-id>`) is for the demo; production is the customer's own resources, in their account, under their IAM.

**One-liner for a customer:**
> "Connecting is config-only — the same AWS MCP servers (Neptune, Athena, HealthOmics) point at *your* resources in *your* account, and the skills adapt to your schema automatically. The work is the one-time step of landing your data in the right AWS service (S3 + Athena for tabular, Neptune for graph) and harmonizing identifiers so sources join — we provide a reference pipeline for exactly that. Public sources (PubMed, ClinicalTrials.gov, Open Targets) need nothing — they're already wired."

---

## Why it's largely plug-and-play

1. **The AWS MCP servers carry no data of their own.** `amazon-neptune` and `aws-dataprocessing` query whatever you point them at. Bringing your own data = changing `NEPTUNE_ENDPOINT` / the Athena database env var to the customer's resources, with their IAM. That's configuration, not code.
2. **The skills are schema-discovery-first.** `oncology-semantic-hub-analysis` calls `get_graph_schema()` / `list-table-metadata` at runtime and composes fresh Cypher/SQL from what it finds ("generate queries, don't memorize"). So a different schema usually needs **no skill rewrite**.

---

## By data type

| Customer data | Target AWS shape | MCP server | Bring-your-own effort |
|---|---|---|---|
| **Patient / genomic data** (like TCGA) | S3 (Parquet) + Glue catalog + Athena DB, partitioned | `aws-dataprocessing` | Land in S3, define Glue tables. One-time ETL. |
| **Knowledge graph** (internal pathways, target–disease links) | Neptune graph (bulk-load nodes/edges CSV) | `amazon-neptune` | Model as nodes/edges, bulk-load. Skill adapts to new labels via live discovery. |
| **Clinical trials — public** | none (already external) | `clinical-trials` / Biomni `query_clinicaltrials` | **Zero** — already available. |
| **Clinical trials — internal/proprietary** | S3 + Athena (tabular) or Neptune (as edges) | `aws-dataprocessing` / `amazon-neptune` | Same ETL pattern as patient data. |
| **Omics files / pipelines** | AWS HealthOmics stores | `aws-healthomics` | Load to HealthOmics. |
| **Internal documents / prior reports** | Bedrock Knowledge Base (RAG) over S3 | (Knowledge Base, via agent) | Index into a KB. |

A ready reference for ingestion lives at `oncology_semantic_hub/scripts/` — 14 numbered scripts (download → build ID mappings → transform to Neptune CSVs → load graph → build the Athena lake → enrich), ~$70/month steady-state. Customers clone this pattern for their own data.

---

## Build your own semantic hub *and* agentic retrievals (the full accelerator)

Bringing your own data isn't only about *connecting* sources — you get the complete pattern to
stand up your own semantic hub, your own agentic retrieval layer, and the evidence that it works
on *your* data:

1. **Your hub.** The ingestion pattern (`scripts/`) lands your data in the right AWS shape —
   your enterprise/knowledge graph into Neptune, your cohort/tabular data into S3 + Athena, with
   ontology enrichments on top. (Reference implementation used PrimeKG + TCGA; you swap in yours.)
2. **Your agentic retrievals.** The deterministic tools the agent calls are reusable as-is,
   pointed at your resources: `query_knowledge_graph` (openCypher/Neptune), `query_patient_data`
   (Athena SQL), `ontology_lookup` (OLS for authoritative identifier resolution), and
   `get_hub_schema`. Because the tools/skills are **schema-discovery-first**, the agent composes
   fresh queries against your schema — no per-customer rewrite. This is the "context engine" that
   turns a bare LLM into a reliable retriever over your deployed data.
3. **Proof it works — on your data.** The validation framework (`evaluation/`) is portable:
   regenerate a golden dataset from *your* pinned snapshot (`generate_questions.py` templates),
   run the with/without-hub comparison (`run_evaluation.py`: L1 raw-lake vs L3 full-hub), score it
   deterministically + LLM-as-judge (`scoring.py` / `judge.py`), and produce a report + dashboard
   (`generate_report.py`). You reproduce, on your own data, the same kind of result the reference
   hub shows — **correctness 52% → 94% and reproducibility 49% → 92% by adding the semantic map,
   with no change to the model** — so you can quantify the value before you depend on it.

**Net:** BYOD delivers (a) your own hub, (b) your own deterministic agentic-retrieval tools, and
(c) a benchmark that proves the semantic layer improves accuracy and reproducibility for your data —
all in your AWS account, portable to AgentCore Runtime for scale.

---

## What's *not* free (the honest caveats)

1. **Ingestion into AWS shape** — the one-time ETL above. The pipeline is templated, but it's real work scaled to the customer's data volume and formats.
2. **Identifier harmonization for cross-system value** — the "1 + 1 = 3" Athena↔Neptune joins need a **shared key** (the hub used Hugo gene symbols + MONDO disease IDs, built by a curation/mapping layer). If the customer's lake and graph use different identifiers, that mapping is required — which is exactly what **OLS** (`ontology-lookup-service`) + a small mapping table provide. This is the glue, and where most "make it actually join" effort goes.
3. **Security / PHI** — TCGA is public; customer patient data is typically PHI. It stays in **their** account with their KMS encryption, least-privilege IAM, and a BAA — and you would *not* casually pass `--allow-sensitive-data-access`; you'd scope IAM tightly. Data sovereignty is a feature of this architecture (nothing is exfiltrated), but it's a deliberate setup step, not automatic.
4. **Identity** — gateway/runtime MCP servers (Biomni, OLS) authenticate with Cognito/OAuth tokens; AWS-public servers use the customer's IAM. Wired once.
5. **Optional skill sharpening** — live discovery means no rewrite, but adding a few customer-schema sample queries + caveats to a skill's `references/` (authoring, not code) improves accuracy on their data.

---

## How to frame it (talking points)

- **Config at the edge, ETL at the source.** The connection is plug-and-play; the data landing is a one-time, templated step.
- **Your data, your account.** Internal sources are reached through the customer's own AWS account and IAM — nothing leaves their boundary. PHI stays compliant.
- **Public sources are already wired.** PubMed, ClinicalTrials.gov, Open Targets, UniProt, etc. need no bring-your-own work.
- **The skills adapt.** Schema-discovery-first means the same skills work on the customer's schema without a rewrite.
- **The glue is harmonization.** The differentiated cross-source value depends on shared identifiers / ontology mapping — that's the highest-leverage piece to get right, and OLS + a mapping layer handle it.
- **We give you the blueprint.** The reference ingestion pipeline is the starting template, not a black box.
