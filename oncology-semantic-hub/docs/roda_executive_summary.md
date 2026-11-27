# RODA Datasets for Oncology Semantic Hub — Executive Summary

> **Date:** 30 July 2026 | **Author:** Hasan Poonawala**Context:** AWS Open Data Registry (RODA) datasets discoverable via RODA MCP server for the Oncology Biomarker Semantic Hub + AgentCore agentic system

---

## Overview

28 datasets identified across 7 modalities. Categorized by readiness for integration into the semantic hub (Neptune graph + Athena data lake) and agentic query system (Bedrock AgentCore + Strands Agents).

**Categorization criteria:**

- **Immediate** — Structured/tabular, openly licensed, same region (us-west-2), directly queryable via Athena or Neptune with minimal transformation. Agent-ready within days.
- **Short-term** — Requires moderate ETL (format conversion, schema mapping) or HealthOmics workflow processing. Agent-ready within 2–4 weeks.
- **Longer-term** — Requires compute-heavy pipelines (WGS variant calling, imaging ML, controlled access approval). Agent-ready in 1–3 months.

---

## 🟢 Immediate (query-ready in <1 week)

Tabular dumps on S3, open license, minimal transformation needed. Download → Parquet → Athena table OR parse → Neptune edges.

| # | Dataset | Modality | S3 Region | License | What It Adds to the Agent |
| --- | --- | --- | --- | --- | --- |
| 1 | **CIViC** | Variant actionability | us-west-2 ✓ | CC0 | "Is this mutation clinically actionable? What drugs have evidence?" |
| 2 | **Genoxus Annotation** | Variant annotation | us-west-2 ✓ | CC-BY 4.0 | Enriched ClinVar — "What's the pathogenicity + disease association for this variant?" |
| 3 | **SnpEff** | Variant effect prediction | us-east-2 | MIT | "What functional consequence does this mutation have on the protein?" |
| 4 | **Beat AML (open)** | Expression + drug response | us-east-1 | NIH GDS | "Which drugs are effective against FLT3-mutated AML?" |
| 5 | **CPTAC-3 (open)** | Proteogenomics expression | us-east-1 | NIH GDS | "What genes are differentially expressed in proteogenomically-characterized tumors?" |
| 6 | **CCLE** | Cancer cell line genomics | us-east-1 | NIH GDS | "Which cell lines have this mutation? What's their drug sensitivity?" |

**Total effort:** ~20 hours | **Agent impact:** Unlocks variant interpretation, drug actionability, and expression queries immediately.

---

## 🟡 Short-term (2–4 weeks)

Requires Python SDK extraction, graph ETL, or moderate data transformation. Some need cross-region S3 copy.

| # | Dataset | Modality | Processing | What It Adds to the Agent |
| --- | --- | --- | --- | --- |
| 7 | **CELLxGENE Census** | Single-cell expression | TileDB-SOMA SDK → marker extraction | "What's the normal expression of EGFR? In which cell types?" |
| 8 | **ESM Atlas** | Protein structure/embeddings | us-west-2 subset download → vector properties | "Find proteins structurally similar to this drug target" |
| 9 | **ENCODE** | Regulatory elements | Selective download (cancer cell lines) → Neptune edges | "Does this non-coding mutation fall in an active regulatory element?" |
| 10 | **UK Biobank Pan-GWAS** | Germline risk (7,221 phenotypes) | TSV summary stats → Athena | "What germline variants increase susceptibility to this cancer?" |
| 11 | **Cell Painting Gallery** | Drug mechanism-of-action | CSV profiles → Parquet + Neptune edges | "Which drugs have similar cellular phenotypes (MoA clustering)?" |
| 12 | **DeepDrug DPEB** | Protein embeddings (human) | JSONL → Neptune vector properties | "Predict novel PPI partners for this gene" |
| 13 | **HCMI** | Tumor organoid models | GDC RNA-Seq → Athena | "Which organoid models exist for this mutation?" |
| 14 | **MMRF CoMMpass** | Myeloma longitudinal | GDC files → Athena | "How does expression change over treatment in myeloma?" |

**Total effort:** ~40 hours | **Agent impact:** Adds normal tissue baselines, protein structure, regulatory context, germline risk, and drug MoA.

---

## 🔴 Longer-term (1–3 months)

Requires HealthOmics workflows (VEP annotation pipelines), controlled-access approval (dbGaP/DACO), or specialized ML infrastructure.

| # | Dataset | Modality | Processing Pipeline | What It Adds to the Agent |
| --- | --- | --- | --- | --- |
| 15 | **1000 Genomes** | Population allele freq | HealthOmics VEP → S3 Tables → Athena | "Is this variant common in the population (germline) or rare (somatic)?" |
| 16 | **ICGC PCAWG** | Whole-genome mutations | DACO approval + HealthOmics VEP | "What non-coding drivers exist across cancer types?" |
| 17 | **Kids First** | Pediatric WGS (30+ studies) | dbGaP approval + HealthOmics pipeline | "What are the driver mutations in pediatric neuroblastoma?" |
| 18 | **Exceptional Responders** | Drug response WES/WGS | HealthOmics VEP → S3 Tables | "What molecular features predict exceptional drug response?" |
| 19 | **MP2PRT** | Treatment resistance trios | HealthOmics somatic calling | "What changes between primary tumor and relapse?" |
| 20 | **RADIANT** | Pediatric brain (multi-modal) | Controlled access + imaging pipeline | "Multimodal pediatric brain tumor atlas" |
| 21 | **CAMELYON** | Histopathology WSI | Pathology AI inference | "Correlate tumor morphology with genotype" |
| 22 | **CHIMERA** | MRI + H&E + RNA-seq | Multimodal ML alignment | "Does combining imaging + genomics improve prognosis?" |
| 23 | **mCRPC** | Metastatic prostate WGS | HealthOmics pipeline | "Resistance mechanisms in metastatic prostate cancer" |
| 24 | **LUAD-EAGLE** | Lung adeno WGS | HealthOmics pipeline | "Environmental + genetic lung cancer etiology" |
| 25 | **CGCI** | Burkitt/cervical WGS | HealthOmics pipeline | "Non-coding mutations in rare lymphoma" |

**Total effort:** ~80+ hours | **Agent impact:** Extends to whole-genome, pediatric, resistance mechanisms, multimodal imaging, and population genetics.

---

## Processing Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │         RODA S3 Open Data Buckets            │
                    └────────┬──────────────┬──────────────┬──────┘
                             │              │              │
              ┌──────────────┼──────────────┼──────────────┼──────────────┐
              │              ▼              ▼              ▼              │
              │  ┌────────────────┐  ┌───────────┐  ┌──────────────┐    │
              │  │ 🟢 IMMEDIATE   │  │ 🟡 SHORT  │  │ 🔴 LONGER    │    │
              │  │ TSV/CSV/MAF    │  │ SDK/ETL   │  │ HealthOmics  │    │
              │  │ → Parquet      │  │ → Parquet │  │ VEP pipeline │    │
              │  │ → Athena       │  │ → Athena/ │  │ → S3 Tables  │    │
              │  │                │  │   Neptune │  │ → Athena     │    │
              │  └───────┬────────┘  └─────┬─────┘  └──────┬───────┘    │
              │          │                 │               │            │
              │          └────────┬────────┴───────┬───────┘            │
              │                   ▼                ▼                    │
              │        ┌──────────────────┐  ┌─────────────────┐       │
              │        │ Athena SQL       │  │ Neptune Graph   │       │
              │        │ (patient data,   │  │ (relationships, │       │
              │        │  variants, expr) │  │  embeddings)    │       │
              │        └────────┬─────────┘  └────────┬────────┘       │
              │                 │                      │                │
              │                 └──────────┬───────────┘                │
              │                            ▼                            │
              │              ┌──────────────────────────┐               │
              │              │  Bedrock AgentCore       │               │
              │              │  (Strands Agent + MCP)   │               │
              │              │                          │               │
              │              │  "Which patients have    │               │
              │              │   pathogenic BRCA1       │               │
              │              │   variants with approved │               │
              │              │   targeted therapy?"     │               │
              │              └──────────────────────────┘               │
              └────────────────────────────────────────────────────────┘

```

**Reference implementation:** [HealthOmics + AgentCore variant interpretation blog](https://aws.amazon.com/blogs/machine-learning/accelerating-genomics-variant-interpretation-with-aws-healthomics-and-amazon-bedrock-agentcore/) (Sandanaraj, Lee & Poonawala, 2025)

---

## Impact Summary

| Horizon | Datasets | New Agent Capabilities |
| --- | --- | --- |
| **Immediate** | 6 | Variant actionability, drug evidence, expression queries, cell line lookups |
| **Short-term** | 8 | Normal expression baselines, protein structure, regulatory context, germline risk, drug MoA |
| **Longer-term** | 11 | Whole-genome non-coding drivers, pediatric cancers, treatment resistance, multimodal imaging |
| **Total** | **25 unique** | Full precision oncology query portfolio |

---

## Not on RODA (require separate download)

| Source | Status | Notes |
| --- | --- | --- |
| COSMIC | ❌ Not on RODA | Download from Sanger (academic license) — already enriching 74 Tier-1 genes |
| IntOGen | ❌ Not on RODA | Download directly from intogen.org |
| DrugBank | ❌ Not on RODA | Academic license required — already in hub via PrimeKG |
| STRING / PharmGKB / ChEMBL | ❌ Not on RODA | Already partially covered via PrimeKG's 20 integrated sources |
| GTEx | ❌ Not on RODA | CELLxGENE Census (on RODA) supersedes at single-cell resolution |
| Open Targets | ❌ Not on RODA | Download from platform.opentargets.org |

