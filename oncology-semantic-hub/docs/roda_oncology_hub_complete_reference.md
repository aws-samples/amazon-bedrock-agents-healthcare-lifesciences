# RODA Open Data Datasets for Oncology Semantic Hub — Complete Reference

> **Author:** Hasan Poonawala  
> **Date:** 30 July 2026  
> **Purpose:** Comprehensive catalog of AWS Registry of Open Data (RODA) datasets discoverable via the RODA MCP server for augmenting the Oncology Biomarker Semantic Hub. Organized by modality, processing method, and integration priority.

---

## Executive Summary

The Oncology Semantic Hub currently integrates TCGA (mutations, CNA, expression), PrimeKG (drug/disease/gene/pathway relationships), ClinVar (pathogenic variant counts), and COSMIC (Tier 1 driver genes). This document identifies **28 high-value datasets** from the AWS Registry of Open Data (RODA) that can be consumed directly from S3.

**Key metrics:**
- 28 datasets across 7 modalities
- 11 are Athena-queryable (tabular → Parquet → SQL)
- 8 are Neptune-loadable (graph ETL → openCypher)
- 9 require specialized processing (ML/imaging/WGS)
- 8 datasets in us-west-2 (same region = zero egress)
- ~78 hours total integration effort across 7 phases

---

## Part 1: Dataset Inventory by Modality & Processing Method

## Why TCGA Isn't Listed Separately

The S3 bucket `s3://tcga-2-open` (referenced in your `data-sources-comparison.md`) **exists on AWS** and is freely accessible, but it is **not formally registered** in the RODA open data catalog. It's part of the GDC NIH STRIDES infrastructure but wasn't submitted as a standalone RODA entry. You're already consuming it via your existing Athena `tcga_mutations` / `tcga_expression` tables — so it's already integrated into the hub.

However, **other GDC programs ARE on RODA** under the STRIDES tag, effectively giving you "more TCGA-like data" from the same ecosystem:

---

## Complete Dataset Inventory (27 datasets)

### By Modality

#### 🧬 Genomics (Somatic Mutations, WES/WGS, Structural Variants)

| # | Dataset | Slug | Modality Detail | S3 Bucket | Region |
|---|---------|------|----------------|-----------|--------|
| 1 | ICGC PCAWG | `icgc` | WGS BAMs/VCFs, 2,400+ whole genomes | `s3://icgc` | us-east-1 |
| 2 | Beat AML 1.0 | `beataml` | WES mutations + RNA-Seq | `s3://gdc-beataml1-cohort-phs001657-2-open` | us-east-1 |
| 3 | Kids First | `kids-first` | WGS, pediatric tumors (30+ studies) | Multiple buckets | us-east-1 |
| 4 | CGCI | `cgci` | WGS + targeted seq (Burkitt/cervical) | `s3://gdc-cgci-phs000235-2-open` | us-east-1 |
| 5 | Exceptional Responders | `exceptional-responders` | WES + WGS + targeted seq | `s3://gdc-exceptional-responders-er-phs001145-2-open` | us-east-1 |
| 6 | MP2PRT | `mp2prt` | WGS 30× (normal→primary→relapse trios) | `s3://gdc-mp2prt-wt-phs001965-2-open` | us-east-1 |
| 7 | mCRPC | `mcrpc` | WGS of metastatic prostate biopsies | GDC bucket | us-east-1 |
| 8 | LUAD-EAGLE | `luad-eagle` | WGS + WES of lung adenocarcinoma | GDC bucket | us-east-1 |
| 9 | CTSP-DLBCL | `ctsp-dlbcl` | Diffuse large B-cell lymphoma sequencing | GDC bucket | us-east-1 |
| 10 | CCLE | `ccle` | Cancer Cell Line Encyclopedia (1,000+ lines) | GDC bucket | us-east-1 |

#### 📊 Transcriptomics (RNA-Seq, miRNA, Gene Expression)

| # | Dataset | Slug | Modality Detail | Region |
|---|---------|------|----------------|--------|
| 11 | CELLxGENE Census | `biohub-cellxgene-census` | Single-cell RNA-seq (tens of millions of cells) | us-west-2 |
| 12 | CPTAC-3 | `cptac-3` | RNA-Seq gene expression + proteogenomics | us-east-1 |
| 13 | HCMI | `hcmi-cmdc` | RNA-Seq from tumor organoid models | us-east-1 |
| 14 | MMRF CoMMpass | `mmrf-commpass` | RNA-Seq longitudinal (multiple myeloma) | us-east-1 |
| 15 | Pancreatic Organoid | `organoid-pancreatic` | WGS + RNA-Seq of pancreatic organoids | us-east-1 |

#### 💊 Pharmacology & Drug Response

| # | Dataset | Slug | Modality Detail | Region |
|---|---------|------|----------------|--------|
| 16 | CIViC | `civic` | Variant-level clinical actionability evidence | us-west-2 |
| 17 | Cell Painting Gallery | `cellpainting-gallery` | Drug morphological profiling (30K+ compounds) | us-east-1 |
| 18 | Beat AML 1.0 | `beataml` | Functional drug sensitivity + genomics | us-east-1 |

#### 🧪 Proteomics & Protein Structure

| # | Dataset | Slug | Modality Detail | Region |
|---|---------|------|----------------|--------|
| 19 | ESM Atlas | `biohub-esm-atlas` | 6.8B protein embeddings + 1.1B structures | us-west-2 |
| 20 | DeepDrug DPEB | `deepdrug-dpeb` | Human protein embeddings (4 modalities) | us-west-2 |
| 21 | AI3 Protein-Ligand | `ai3` | Protein-ligand binding affinity | — |

#### 🔬 Variant Annotation & Population Genetics

| # | Dataset | Slug | Modality Detail | Region |
|---|---------|------|----------------|--------|
| 22 | Genoxus Annotation | `genoxus-annotation` | Harmonized ClinVar (SNVs, INDELs, CNVs, SVs) | us-west-2 |
| 23 | SnpEff | `snpeff` | Variant effect prediction databases | us-east-2 |
| 24 | 1000 Genomes | `1000-genomes` | Population allele frequencies (2,500 individuals) | us-east-1 |
| 25 | UK Biobank Pan-GWAS | `broad-pan-ukb` | 7,221 phenotype GWAS summary stats | us-east-1 |

#### 🖼️ Imaging (Histopathology, Radiology)

| # | Dataset | Slug | Modality Detail | Region |
|---|---------|------|----------------|--------|
| 26 | CAMELYON | `camelyon` | 1,399 H&E whole-slide images (breast metastasis) | us-west-2 |
| 27 | CHIMERA | `chimera` | Paired MRI + H&E + RNA-seq + clinical | us-west-2 |

#### 🧬 Epigenomics & Regulatory

| # | Dataset | Slug | Modality Detail | Region |
|---|---------|------|----------------|--------|
| 28 | ENCODE | `encode-project` | TF binding, chromatin, methylation, enhancers | us-west-2 |

---

## Processing Classification

### ✅ Athena-Queryable (tabular/structured → download → Parquet → Athena table)

These datasets produce **structured tabular data** (TSV/CSV/MAF/VCF) that can be converted to Parquet and queried directly in your existing `oncology_semantic_hub` Athena database.

| Dataset | Source Format | Athena Table Name (proposed) | Join Key to Hub |
|---------|------|------|------|
| **CIViC** | TSV dumps (evidence, assertions, variants) | `civic_evidence`, `civic_variants` | `hugo_symbol` → gene_protein.name |
| **Genoxus Annotation** | Structured ClinVar (TSV/JSON) | `clinvar_harmonized` | chr:pos:ref:alt → tcga_mutations |
| **1000 Genomes** | VCF (allele frequencies) | `population_allele_freq` | chr:pos:ref:alt → tcga_mutations |
| **UK Biobank Pan-GWAS** | TSV summary stats | `gwas_cancer_associations` | gene/variant → gene_protein |
| **Beat AML (open)** | GDC RNA-Seq TSV | `beataml_expression` | hugo_symbol, case_id |
| **CPTAC-3 (open)** | GDC RNA-Seq TSV | `cptac3_expression` | hugo_symbol, case_id |
| **CCLE** | GDC processed files | `ccle_expression`, `ccle_mutations` | hugo_symbol |
| **MMRF CoMMpass** | GDC processed files | `mmrf_expression` | hugo_symbol, case_id |
| **ICGC (metadata)** | XML analysis metadata | `icgc_samples` | donor_id, cancer_type |
| **SnpEff** | Annotation DB (TSV) | `snpeff_consequences` | chr:pos:ref:alt |
| **HCMI** | GDC RNA-Seq | `hcmi_expression` | hugo_symbol |

**Processing pipeline:** S3 → Glue Crawler / Python ETL → Parquet on S3 → Athena table → SQL queries  
**Effort per dataset:** 2–4 hours

---

### ✅ Neptune-Loadable (graph-structured → nodes/edges → openCypher)

These datasets produce **relationship/network data** that should be loaded as nodes and edges into your Neptune Analytics graph.

| Dataset | New Node Types | New Edge Types | Join Key to Hub |
|---------|----------------|----------------|-----------------|
| **CIViC** | `clinical_evidence`, `assertion` | `variant_has_evidence`, `evidence_supports_drug` | gene_protein.name, drug.name |
| **Genoxus Annotation** | — (enrich existing) | Updates `clinvar_pathogenic_count` → full annotation properties | gene_protein node properties |
| **ENCODE** | `regulatory_element` | `gene_regulated_by`, `active_in_tissue` | gene_protein.name, anatomy.name |
| **ESM Atlas** | — (enrich existing) | Adds vector properties to gene_protein nodes | UniProt ID → gene_protein |
| **DeepDrug DPEB** | — (enrich existing) | Adds embedding vectors to gene_protein | UniProt ID → gene_protein |
| **Cell Painting** | `compound_profile` | `drug_has_phenotype`, `drug_similar_moa` | drug.name (DrugBank mapping) |
| **Kids First / RADIANT** (cases) | `case` (pediatric) | `case_has_diagnosis`, `sample_from_case` | disease.name (MONDO) |
| **Exceptional Responders** (cases) | `case` (exceptional) | `case_has_diagnosis`, `case_responded_to_drug` | disease, drug |

**Processing pipeline:** Download → Parse → Generate node/edge CSV → `LOAD DATA` or bulk load into Neptune Analytics  
**Effort per dataset:** 3–6 hours

---

### ⚠️ Requires Specialized Processing (not directly Athena/Neptune)

These datasets need **custom ETL, ML pipelines, or specialized tooling** before they can contribute to the hub.

| Dataset | Format | Why Special | Processing Needed | Output for Hub |
|---------|--------|-------------|-------------------|---------------|
|---------|--------|-------------|-------------------|---------------|
| **ICGC (BAMs/VCFs)** | BAM, VCF (100s TB) | Raw sequencing files, too large for Athena | Variant calling → MAF/VCF → Parquet | Athena table: `icgc_mutations` |
| **CELLxGENE Census** | TileDB-SOMA (AnnData) | Specialized sparse matrix format | Python SDK → extract tissue-specific markers → TSV | Athena: `cellxgene_markers`; Neptune: cell_type properties |
| **CAMELYON** | TIFF whole-slide images | Gigapixel images, not tabular | Deep learning inference (pathology AI) | Neptune: image-derived features as case properties |
| **CHIMERA** | DICOM (MRI) + TIFF (H&E) + TSV | Multimodal, needs alignment | Multimodal ML pipeline | Neptune: imaging features linked to cases |
| **Cell Painting Gallery** | TIFF images + CSV profiles | Image features pre-extracted to CSV | CSV profiles → Parquet → Athena | Athena: `cellpainting_profiles`; Neptune: drug MoA edges |
| **ESM Atlas (structures)** | PDB/mmCIF files | 3D structure files | Structure comparison tools | Neptune: structural similarity edges |
| **Kids First (WGS)** | BAM/CRAM (controlled) | Requires dbGaP access + variant calling | Same as ICGC | Athena: `kidsfirst_mutations` |
| **RADIANT (imaging)** | DICOM + H&E | Radiology + pathology images | Imaging AI pipeline | Neptune: imaging biomarker nodes |
| **MP2PRT (WGS)** | BAM (raw) | Requires alignment + variant calling | Standard WGS pipeline | Athena: `mp2prt_mutations` |

---

### 🔄 HealthOmics Workflow Pipeline (for VCF/BAM datasets)

For raw genomic datasets (VCF, BAM), the proven processing pattern is **AWS HealthOmics → S3 Tables → Agent queries** — as demonstrated in [Accelerating genomics variant interpretation with AWS HealthOmics and Amazon Bedrock AgentCore](https://aws.amazon.com/blogs/machine-learning/accelerating-genomics-variant-interpretation-with-aws-healthomics-and-amazon-bedrock-agentcore/) (Sandanaraj, Lee & Poonawala, Nov 2025).

**Pipeline:**
```
┌────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│ RODA S3    │────▶│ HealthOmics      │────▶│ S3 Tables       │────▶│ Agent Query  │
│ (raw VCF/  │     │ Workflow (VEP +   │     │ (Iceberg/       │     │ (Athena SQL  │
│  BAM files)│     │  ClinVar annot.) │     │  Parquet)       │     │  via NL)     │
└────────────┘     └──────────────────┘     └─────────────────┘     └──────────────┘
```

**What it does:**
1. Raw VCF files from RODA S3 → HealthOmics runs VEP annotation (functional predictions + ClinVar clinical annotations)
2. Annotated VCFs → transformed to structured S3 Tables (optimized for query)
3. Strands Agent on AgentCore → natural language interface for researchers to ask "Which patients have pathogenic BRCA1 variants?"

**Datasets best suited for this pipeline:**

| Dataset | Input | Scale | HealthOmics Workflow |
|---------|-------|-------|---------------------|
| **1000 Genomes** | VCF (population variants) | 85M variants, 2,500 samples | VEP annotation → S3 Tables |
| **ICGC PCAWG** | WGS VCFs | 2,400+ whole genomes | VEP + ClinVar annotation |
| **Kids First** | WGS BAMs/CRAMs | 30+ pediatric studies | Alignment + variant calling + VEP |
| **MP2PRT** | WGS BAMs | 70 trios (normal→primary→relapse) | Somatic calling + VEP |
| **mCRPC** | WGS | Metastatic prostate biopsies | Somatic calling + VEP |
| **LUAD-EAGLE** | WGS + WES | 31 lung adenocarcinoma samples | VEP annotation |
| **Exceptional Responders** | WES + WGS | ~100 cases | VEP + ClinVar annotation |

**Key advantage:** Removes the bioinformatics bottleneck — once processed, clinical researchers query via natural language without SQL expertise.

**Reference implementation:** [GitHub — starter agents for life sciences on AWS](https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences)

---

### Processing Decision Tree

```
Is the dataset already tabular (TSV/CSV/MAF)?
  ├── YES → Parquet conversion → Athena table (2-4 hrs)
  │         Examples: CIViC, Genoxus, BeatAML expression, CCLE
  │
  └── NO → Is it VCF/BAM (raw genomic)?
            ├── YES → HealthOmics VEP pipeline → S3 Tables → Athena (8-20 hrs)
            │         Examples: 1000 Genomes, ICGC, Kids First, MP2PRT
            │
            └── NO → Is it graph/relational?
                      ├── YES → ETL → Neptune node/edge CSV → openCypher load (3-6 hrs)
                      │         Examples: ENCODE regulatory, ESM embeddings, CIViC edges
                      │
                      └── NO → Specialized ML pipeline (imaging, sparse matrix)
                                Examples: CAMELYON, CHIMERA, CELLxGENE
```

---

## Summary Matrix

| Processing Method | Count | Datasets | Typical Effort |
|-------------------|-------|----------|---------------|
| **Athena-ready** (tabular → Parquet → query) | 11 | CIViC, Genoxus, 1KG, UKB-GWAS, BeatAML, CPTAC-3, CCLE, MMRF, ICGC meta, SnpEff, HCMI | 2–4 hrs each |
| **Neptune-loadable** (graph ETL) | 8 | CIViC*, Genoxus*, ENCODE, ESM Atlas, DPEB, Cell Painting, Kids First cases, Exceptional Responders cases | 3–6 hrs each |
| **Specialized processing** | 9 | ICGC BAMs, CELLxGENE, CAMELYON, CHIMERA, Cell Painting images, ESM structures, Kids First WGS, RADIANT, MP2PRT | 8–20 hrs each |

*CIViC and Genoxus appear in both Athena AND Neptune because their tabular data creates Athena tables AND their relationship data creates Neptune edges.

---

## Region Distribution

| Region | Datasets | Notes |
|--------|----------|-------|
| **us-west-2** (same as hub) | CIViC, CELLxGENE, Genoxus, ESM Atlas, DPEB, ENCODE, CAMELYON, CHIMERA | ✅ Zero egress cost, lowest latency |
| **us-east-1** | 1KG, UKB-GWAS, BeatAML, ICGC, CPTAC-3, CCLE, MMRF, Kids First, RADIANT, HCMI, CGCI, MP2PRT, mCRPC, LUAD, CTSP, Exceptional Responders, Pancreatic Organoid | Cross-region S3 copy needed (one-time) |
| **us-east-2** | SnpEff | Cross-region copy |

---

## Quick-Start Recommendations

### If you want to add value in 1 day:
→ **CIViC** (CC0, us-west-2, monthly TSV dumps) — creates both Athena tables AND Neptune edges. Unlocks: "What is the clinical evidence for this variant?"

### If you want the biggest modality expansion:
→ **CELLxGENE Census** (single-cell expression baseline) + **ESM Atlas** (protein structure/embeddings) — adds two entirely new data dimensions the hub currently lacks.

### If you want to expand cancer type coverage:
→ **CCLE** (1,000+ cell lines) + **MMRF CoMMpass** (myeloma) + **Kids First** (pediatric) — triples the number of cancer contexts beyond TCGA's 33.

### If you want multimodal AI:
→ **CHIMERA** (radiology + pathology + molecular + clinical) — the only dataset combining ALL four modalities in paired patients.


---
---

## Part 2: Detailed Dataset Profiles & Integration Plans

## Current Hub Architecture (Context)

| Layer | Scale | Source |
|-------|-------|--------|
| Neptune Analytics graph | 174,742 nodes, 4,095,616 edges | PrimeKG + TCGA cases/samples + ClinVar + COSMIC |
| Athena patient data lake | ~1.83M somatic mutations, ~44K expression z-scores, ~1.7M CNAs | TCGA (33 cancer types) |
| Cross-system join coverage | 99% gene matching (Hugo Symbol ↔ gene_protein.name) | — |

### Existing Correlation Keys
- **Patient level:** TCGA barcode → GDC ↔ cBioPortal ↔ TCIA
- **Gene level:** Hugo Symbol → PrimeKG ↔ ClinVar ↔ COSMIC
- **Disease level:** MONDO ID → PrimeKG ↔ TCGA projects ↔ ICD-10
- **Variant level:** chr:pos:ref:alt → GDC mutations ↔ ClinVar ↔ COSMIC

---

## Tier 1 — Directly Integrable (High Impact, Low Effort)

### 1. CIViC (Clinical Interpretation of Variants in Cancer)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `civic` |
| **S3 bucket** | `s3://civic-aws-opendata` |
| **Region** | us-west-2 |
| **License** | CC0 (Public Domain) |
| **Update frequency** | Monthly (1st of each month) |
| **Managed by** | Griffith Lab, Washington University School of Medicine |
| **Format** | Monthly data dumps: feature, variant, assertion, and evidence tables |

**Hub Integration Value:**
- Adds **variant-level clinical evidence** edges: `mutation → drug_response`, `mutation → actionability_level`
- Maps directly to existing hub genes via Hugo Symbol
- Complements ClinVar (pathogenicity) with **therapeutic actionability** (drug response evidence)
- Fills the gap identified in `data-sources-comparison.md`: "OncoKB / CIViC = variant → actionability level"

**Correlation to Hub:**
- Gene-level: Hugo Symbol → `gene_protein.name` (same join key)
- Variant-level: chr:pos:ref:alt → can link to `tcga_mutations`
- Disease-level: CIViC diseases can map to MONDO via OLS

**Integration Effort:** ~3 hours (download monthly dump, parse evidence/assertion tables, create edges)

**New edge types enabled:**
- `variant_has_evidence` (variant → clinical evidence)
- `variant_predicts_sensitivity` / `variant_predicts_resistance` (variant → drug)

---

### 2. ICGC PCAWG (Pan-Cancer Analysis of Whole Genomes)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `icgc` |
| **S3 bucket** | `s3://icgc` (BAMs/VCFs), `s3://oicr.icgc.meta/metadata` (analysis metadata) |
| **Region** | us-east-1 |
| **License** | Controlled access (ICGC DACO approval required) |
| **Update frequency** | As available |
| **Managed by** | International Cancer Genome Collaboratory |

**Hub Integration Value:**
- **2,400+ whole-genome** BAMs/VCFs from 1,100+ donors across cancer types
- Extends hub beyond TCGA's exome-only data to **non-coding somatic mutations**
- Provides **mutational signatures** (Alexandrov et al., 2020) — a new analytical dimension
- Key publications: non-coding drivers, structural variation, evolutionary history of cancer

**Correlation to Hub:**
- Gene-level: Hugo Symbol (same)
- Disease-level: ICGC cancer types → MONDO (mappable)
- Patient-level: No overlap with TCGA patients, but same cancer types

**Integration Effort:** ~8 hours (DACO approval process + VCF parsing + loading)

**New capabilities enabled:**
- Non-coding driver queries ("What non-coding mutations are recurrent in breast cancer?")
- Mutational signature analysis ("Which TCGA-BRCA patients match the APOBEC signature?")
- Structural variant integration

---

### 3. CELLxGENE Discover Census (Single-Cell Atlas)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `biohub-cellxgene-census` |
| **S3 bucket** | `s3://cellxgene-census-public-us-west-2/cell-census` |
| **Region** | us-west-2 ✓ (same region as hub) |
| **License** | CC-BY 4.0 |
| **Update frequency** | Weekly (new releases), LTS every 6 months |
| **Managed by** | Chan Zuckerberg Biohub |
| **API** | Python/R SDK via TileDB-SOMA |

**Hub Integration Value:**
- **Tens of millions of cells** across all major human tissues
- Provides **normal tissue expression baselines** — the hub currently lacks baseline expression for comparison with TCGA tumor data
- Cell-type-specific gene expression → answers "In which normal cell types is EGFR highly expressed?"
- Replaces/supplements GTEx at single-cell resolution
- Direct alignment with `data-sources-comparison.md` recommendation: "CellxGene = 50M+ cells, largest single-cell resource (P1 priority)"

**Correlation to Hub:**
- Gene-level: Gene symbols → `gene_protein.name`
- Disease-level: Cancer tissue types overlap with TCGA anatomy
- Cell-type-level: NEW dimension — `cell_type` nodes

**Integration Effort:** ~4 hours (Python SDK query → extract tissue-specific marker genes → add as graph properties or new `cell_type` nodes)

**New capabilities enabled:**
- "What cell types normally express TP53 vs where it's mutated in TCGA?"
- "Is this driver gene also expressed in normal tissue?" (tumor-specific vs. housekeeping)
- Cell-type deconvolution context for bulk TCGA samples

---

### 4. Genoxus Annotation (Harmonized ClinVar)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `genoxus-annotation` |
| **S3 bucket** | `s3://genoxus-annotation-release` |
| **Region** | us-west-2 ✓ |
| **License** | CC-BY 4.0 |
| **Update frequency** | Annually + as needed |
| **Managed by** | Genoxus Labs |
| **Added to RODA** | April 2026 (very recent) |

**Hub Integration Value:**
- **Harmonized ClinVar** with standardized disease terminology and consolidated evidence
- Covers SNVs, INDELs, CNVs, and structural variants
- GWAS Catalog integration planned for future releases
- Could **replace or augment** the hub's current ClinVar enrichment (6,286 genes with `clinvar_pathogenic_count`) with richer annotation including disease associations and variant classification reasoning

**Correlation to Hub:**
- Variant-level: chr:pos:ref:alt (standard genomic coordinates)
- Gene-level: Hugo Symbol
- Disease-level: Standardized disease terminology (mappable to MONDO)

**Integration Effort:** ~2 hours (download from S3, parse, update `clinvar_pathogenic_count` with richer fields)

**Upgrade over current approach:**
- Current: Simple count (`clinvar_pathogenic_count = 47`)
- With Genoxus: Per-variant pathogenicity + evidence + disease association

---

### 5. Beat AML 1.0 (Drug Sensitivity + Genomics)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `beataml` |
| **S3 bucket** | `s3://gdc-beataml1-cohort-phs001657-2-open` (open), `s3://gdc-beataml1-cohort-phs001657-2-controlled` (controlled) |
| **Region** | us-east-1 |
| **License** | NIH Genomic Data Sharing Policy |
| **Managed by** | Center for Translational Data Science, U. Chicago |
| **Source of truth** | GDC (monthly updates) |

**Hub Integration Value:**
- **First drug sensitivity data** in the hub — genomic profiles + functional drug response for AML patients
- 11 academic medical centers, largest AML functional genomics dataset
- Open data includes: RNA-Seq Gene Expression Quantification, Clinical Supplement
- Controlled data includes: WXS mutations, RNA-Seq aligned reads

**Correlation to Hub:**
- Gene-level: Same Hugo Symbols → `gene_protein.name`
- Drug-level: Drug response data → `drug` nodes in PrimeKG
- Disease-level: AML → MONDO disease node

**Integration Effort:** ~4 hours (open data: expression + clinical → Athena table; mutation data requires dbGaP approval)

**New capabilities enabled:**
- "Which drugs show sensitivity in AML patients with FLT3 mutations?"
- Drug response as a phenotypic layer connecting mutations → drugs
- Functional validation of PrimeKG's `drug_protein` edges

---

## Tier 2 — Strong Complements (Medium Effort)

### 6. Exceptional Responders Initiative

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `exceptional-responders` |
| **S3 bucket** | `s3://gdc-exceptional-responders-er-phs001145-2-open` |
| **Region** | us-east-1 |
| **License** | NIH Genomic Data Sharing Policy |
| **Data types** | WES, WGS, mRNA-seq, miRNA-seq, methylation, targeted sequencing |

**Hub Integration Value:**
- ~100 cancer patients with **exceptional drug responses** (CR or PR >6 months where overall response rate <10%)
- Multi-omics characterization of molecular features driving exceptional responses
- **Drug response biomarker discovery** — directly aligns with the hub's drug→gene→patient query pattern
- Answers: "What molecular features predict exceptional response to therapy X?"

**Correlation to Hub:**
- Gene-level: Hugo Symbol (standard GDC processing)
- Drug-level: Treatment annotations → `drug` nodes
- Disease-level: Cancer types → MONDO

**Integration Effort:** ~4 hours

---

### 7. ENCODE (Encyclopedia of DNA Elements)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `encode-project` |
| **S3 bucket** | `s3://encode-public` |
| **Region** | us-west-2 ✓ |
| **License** | Open (no restrictions) |
| **Update frequency** | Daily |
| **Managed by** | ENCODE Data Coordinating Center |

**Hub Integration Value:**
- Comprehensive catalogue of **regulatory elements**: enhancers, promoters, TF binding sites, chromatin accessibility
- Explains **why non-coding mutations matter** — "This TCGA mutation falls in an active enhancer for EGFR in lung tissue"
- Epigenomic context for driver genes

**Correlation to Hub:**
- Gene-level: Regulatory elements mapped to target genes
- Tissue-level: Cell type / tissue annotations → `anatomy` nodes

**Integration Effort:** ~6 hours (selective — focus on cancer-relevant cell lines)

**New edge types:**
- `gene_regulated_by` (gene ← regulatory element)
- `enhancer_active_in` (regulatory element → tissue)

---

### 8. 1000 Genomes (Population Allele Frequencies)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `1000-genomes` |
| **S3 bucket** | `s3://1000genomes` |
| **Region** | us-east-1 |
| **License** | Open (no restrictions) |
| **Scale** | 2,500+ individuals, 26 populations, 80M+ variants |

**Hub Integration Value:**
- **Germline context** for somatic mutations — filter common polymorphisms from true somatic drivers
- Population allele frequencies enable: "Is this TCGA mutation common in the general population (likely germline artifact) or rare (likely somatic driver)?"
- Adds `population_allele_frequency` property to variant-level queries

**Correlation to Hub:**
- Variant-level: chr:pos:ref:alt → same coordinates as `tcga_mutations`

**Integration Effort:** ~3 hours (extract VCF allele frequencies for TCGA mutation positions)

---

### 9. DeepDrug Protein Embeddings Bank (DPEB)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `deepdrug-dpeb` |
| **S3 bucket** | `s3://deepdrug-dpeb` |
| **Region** | us-west-2 ✓ |
| **License** | MIT |
| **Format** | JSONL with UniProt IDs + embeddings (AlphaFold2, ESM-2, BioEmbeddings, ProtVec) |

**Hub Integration Value:**
- **Pre-computed protein embeddings** for all human proteins
- Enables ML-based predictions directly from graph nodes:
  - PPI prediction (which proteins interact?)
  - Drug-target prediction (which drugs bind this protein?)
  - Functional similarity (which genes have similar functions?)
- UniProt IDs map to PrimeKG `gene_protein` nodes

**Correlation to Hub:**
- Protein-level: UniProt ID → `gene_protein` nodes (mappable via UniProt↔Hugo Symbol)

**Integration Effort:** ~3 hours (download embeddings, map to gene_protein nodes, store as vector properties or separate embedding table)

**New capabilities enabled:**
- Similarity-based drug target expansion: "Find proteins structurally similar to known EGFR inhibitor targets"
- Vector search for novel biomarker candidates

---

### 10. Cell Painting Gallery (Drug Mechanism of Action)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `cellpainting-gallery` |
| **S3 bucket** | `s3://cellpainting-gallery` |
| **Region** | us-east-1 |
| **License** | CC0 (Public Domain) |
| **Managed by** | Carpenter-Singh & Cimini Labs, Broad Institute |

**Hub Integration Value:**
- **30,000+ compounds** with morphological profiling data
- Links drugs to cellular phenotypic responses
- Enables mechanism-of-action inference: "These two drugs cause similar morphological changes → likely same target pathway"
- Publication shows Cell Painting predicts impact of lung cancer variants

**Correlation to Hub:**
- Drug-level: Compound names/IDs → DrugBank IDs → `drug` nodes
- Gene-level: Genetic perturbation datasets include gene knockdowns

**Integration Effort:** ~6 hours (extract compound-level morphological profiles, link to drug nodes)

---

## Tier 3 — Future Expansion

| Dataset | RODA Slug | Value | Priority |
|---------|-----------|-------|----------|
| SnpEff Annotation DBs | `snpeff` | Variant effect prediction (consequence types) | P3 |
| Kids First (Pediatric) | `kids-first` | Pediatric cancer genomics — extends beyond adult TCGA | P3 |
| Allen Ivy Glioblastoma Atlas | `allen-ivy-glioblastoma-atlas` | Spatial gene expression in GBM tumors | P3 |
| AI3 Protein-Ligand Binding | `ai3` | Binding affinity data for drug-target ML models | P3 |
| 4D Nucleome | `4dnucleome` | 3D genome organization (gene fusion context) | P4 |
| Broad Genome References | `broad-references` | Reference builds (hg38) for alignment context | Utility |

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  ONCOLOGY SEMANTIC HUB (Current)                      │
│                                                                       │
│  Neptune Graph (174K nodes)         Athena Lake (~3.5M records)      │
│  • gene_protein (27,671)            • tcga_mutations (1.83M)          │
│  • disease (17,080)                 • tcga_expression (44K)           │
│  • drug (7,957)                     • source_cbioportal (1.7M)        │
│  • pathway (2,516)                                                    │
│  • case/sample (45,367)                                               │
└─────────────────┬───────────────────────────────┬─────────────────────┘
                  │                               │
    ┌─────────────┼───────────────────────────────┼─────────────────┐
    │             │    RODA EXPANSION LAYER        │                 │
    │             ▼                               ▼                 │
    │  ┌──────────────────┐        ┌──────────────────────────┐     │
    │  │ Neptune Enrichment│        │ Athena New Tables         │     │
    │  │                  │        │                          │     │
    │  │ + CIViC evidence │        │ + beataml_drug_response  │     │
    │  │   edges          │        │ + exceptional_responders │     │
    │  │ + ENCODE regula- │        │ + icgc_wgs_mutations     │     │
    │  │   tory elements  │        │ + cellxgene_markers      │     │
    │  │ + DPEB protein   │        │                          │     │
    │  │   embeddings     │        │                          │     │
    │  │ + Genoxus-       │        └──────────────────────────┘     │
    │  │   enriched       │                                         │
    │  │   ClinVar props  │        ┌──────────────────────────┐     │
    │  │ + Cell Painting  │        │ Reference/Filter          │     │
    │  │   MoA edges      │        │                          │     │
    │  └──────────────────┘        │ + 1000genomes_af         │     │
    │                              │   (population freq)       │     │
    │                              └──────────────────────────┘     │
    └───────────────────────────────────────────────────────────────┘
```

---

## Prioritized Implementation Roadmap

| Phase | Datasets | New Queries Enabled | Effort |
|-------|----------|--------------------:|--------|
| **Phase 1** (immediate) | CIViC + Genoxus Annotation | "What is the clinical actionability of this mutation?" "Is this variant pathogenic and in which diseases?" | ~5 hrs |
| **Phase 2** (next sprint) | CELLxGENE + Beat AML | "Normal expression of driver genes?" "Drug sensitivity by genotype?" | ~8 hrs |
| **Phase 3** (enhancement) | ICGC PCAWG + 1000 Genomes | "Non-coding drivers?" "Is this somatic or germline?" | ~11 hrs |
| **Phase 4** (ML-ready) | DPEB + Cell Painting | "Similar proteins to this target?" "Drug MoA clustering?" | ~9 hrs |
| **Phase 5** (epigenomics) | ENCODE + Exceptional Responders | "Regulatory context of mutations?" "What predicts exceptional response?" | ~10 hrs |

**Total estimated effort:** ~43 hours across 5 phases

---

## Key Differentiator: S3-Native Consumption

All RODA datasets are hosted on Amazon S3. This means:

1. **No API rate limits** — unlike GDC API (which took 5 hours for mutations due to pagination)
2. **Same-region access** — CIViC, CELLxGENE, ENCODE, Genoxus, DPEB are all in `us-west-2` (same as the hub)
3. **Zero egress cost** — same-region S3-to-S3 or S3-to-Athena
4. **Athena-queryable** — download once, convert to Parquet, query via existing Athena infrastructure
5. **Reproducible** — versioned S3 objects, no API changes to break pipelines

This aligns with the lesson learned in `data-sources-comparison.md`: "The same data is available on S3 as pre-built files that could be downloaded in ~10 minutes and converted to Parquet locally."

---

## Deep-Search Findings: Additional RODA Datasets (Round 2)

The following datasets were discovered by cross-referencing the `oncology-semantic-hub-requirements.md` enrichment sources (Section 4) against RODA. These directly address gaps identified in the requirements document.

---

### 11. CPTAC-3 (Clinical Proteomic Tumor Analysis Consortium, Phase III)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `cptac-3` |
| **S3 bucket** | `s3://gdc-cptac-phs001287-2-open` |
| **Region** | us-east-1 |
| **License** | NIH Genomic Data Sharing Policy |
| **Data types** | RNA-Seq Gene Expression Quantification (open); Proteomics via Proteomic Data Commons |
| **Managed by** | Center for Translational Data Science, U. Chicago |

**Hub Integration Value:**
- Proteogenomics: links **protein abundance** to genomic alterations in cancer
- Open access RNA-Seq expression from proteogenomically-characterized tumors
- Directly addresses requirements doc Section 2.1 (GDC programs beyond TCGA)
- Integrated proteogenomic characterization papers for clear cell RCC, breast, colon, etc.

**Correlation to Hub:**
- Gene-level: Ensembl IDs → Hugo Symbol → `gene_protein.name`
- Case-level: GDC UUIDs (same ecosystem as TCGA)

**New capabilities:** "What proteins are overexpressed in tumors with TP53 mutations?" / "Proteogenomic validation of graph-predicted drug targets"

---

### 12. ESM Atlas — Protein Features and Structures (6.8B proteins)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `biohub-esm-atlas` |
| **S3 bucket** | `s3://esm-protein-atlas` |
| **Region** | us-west-2 ✓ |
| **License** | CC-BY-SA 4.0 |
| **Scale** | 6.8B protein sequences with SAE features + 1.1B predicted 3D structures |
| **Added to RODA** | May 2026 (very recent) |

**Hub Integration Value:**
- **Massively supersedes DeepDrug DPEB** (Tier 1 #9) — orders of magnitude more proteins
- ESMFold2 predicted structures for drug-target structural analysis
- Sparse Autoencoder (SAE) features = interpretable biological representations
- Functional clustering (7.7M clusters) enables novel function prediction
- Includes **mutation scoring** tutorial — directly applicable to TCGA variant interpretation

**Correlation to Hub:**
- Protein-level: UniProt IDs → `gene_protein` nodes
- Structure-based drug-target prediction complements PrimeKG `drug_protein` edges

**Integration Effort:** ~4 hrs (download human protein subset, map UniProt → Hugo Symbol, add structure/embedding vectors)

---

### 13. CAMELYON (Cancer Metastases in Lymph Nodes Challenge)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `camelyon` |
| **S3 bucket** | `s3://camelyon-dataset` |
| **Region** | us-west-2 ✓ |
| **License** | CC0 (Public Domain) |
| **Data types** | 1,399 H&E whole-slide images with tumor/stroma/TIL annotations |

**Hub Integration Value:**
- **Digital pathology** layer for the hub — breast cancer lymph node metastasis detection
- Annotated whole-slide images with tumor/stroma/TIL boundaries
- Enables multimodal queries: "Show me the histopathology of patients with BRCA1 mutations"
- Requirements doc mentions slide images as a GDC data type — this provides labeled training data

**New capabilities:** Multimodal AI queries bridging genomics ↔ pathology imaging

---

### 14. CHIMERA (Combining Histology, Radiology and Molecular Data)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `chimera` |
| **S3 bucket** | `s3://chimera-challenge` |
| **Region** | us-west-2 ✓ |
| **License** | CC BY-NC-SA 4.0 |
| **Data types** | Paired MRI + H&E slides + RNA-seq + clinical recurrence data |

**Hub Integration Value:**
- **True multimodal cancer dataset**: imaging (MRI + pathology) + molecular (RNA-seq) + clinical (recurrence)
- Task 1: Prostate cancer (MRI + H&E + clinical + biochemical recurrence)
- Task 2-3: Bladder cancer (H&E + clinical + RNA-seq + recurrence)
- Directly demonstrates the "multimodal oncology biomarker" vision of your hub

**New capabilities:** Cross-modal biomarker prediction — "Does combining imaging + genomics improve recurrence prediction?"

---

### 15. UK Biobank Pan-Ancestry GWAS Summary Statistics

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `broad-pan-ukb` |
| **S3 bucket** | `s3://pan-ukb-us-east-1` |
| **Region** | us-east-1 |
| **License** | CC-BY 4.0 |
| **Scale** | 7,221 phenotypes × 16,119 GWAS across multiple ancestries |
| **Managed by** | Broad Institute / MGH |

**Hub Integration Value:**
- Maps **germline genetic risk** to cancer phenotypes across populations
- 7,221 phenotypes include cancer types → identify germline susceptibility loci
- Multi-ancestry analysis → health equity dimension (requirements doc mentions "underrepresented populations" via HCMI)
- Complements somatic mutation data (TCGA) with germline predisposition context

**Correlation to Hub:**
- Gene-level: GWAS hits map to genes → `gene_protein.name`
- Disease-level: Phenotype codes → MONDO/ICD-10 mapping

**New capabilities:** "Which germline variants increase risk for cancers where TP53 somatic mutations are frequent?"

---

### 16. Kids First Pediatric Research Program

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `kids-first` |
| **S3 bucket** | Multiple per-study buckets (30+ S3 buckets) |
| **Region** | us-east-1 |
| **License** | NIH Genomic Data Sharing Policy (mostly controlled) |
| **Scale** | Thousands of children, 30+ studies including pediatric brain tumors, leukemia, neuroblastoma, osteosarcoma |

**Hub Integration Value:**
- **Pediatric cancer genomics** — extends hub beyond adult TCGA
- WGS data (vs TCGA's mostly WES) → better non-coding variant coverage
- Specific studies: neuroblastoma, osteosarcoma, T-ALL, Wilms tumor, Ewing sarcoma
- PedcBioPortal integration (same cBioPortal ecosystem)
- Requirements doc mentions GDC's TARGET program — Kids First is the modern successor

**Key pediatric cancer studies on S3:**
- Neuroblastoma germline genetics
- Osteosarcoma treatment failure analysis
- Pediatric T-cell ALL
- Hematopoietic malignancy familial predisposition
- Children's Brain Tumor Network (CBTN)

---

### 17. RADIANT (Real-time Analysis and Discovery in Integrated And Networked Technologies)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `radiant` |
| **S3 bucket** | `s3://opendata-chop-study-us-east-1-prd-sd-bhjxbdqk` |
| **Region** | us-east-1 |
| **License** | NIH GDS Policy |
| **Data types** | Clinical (EMR), genomics, transcriptomics, proteomics, radiology imaging, pathology imaging |
| **Added to RODA** | March 2025 (recent) |

**Hub Integration Value:**
- **Pediatric brain tumor multimodal atlas** from 35+ partnered health care systems
- Truly multimodal: genomics + transcriptomics + proteomics + radiology + pathology + clinical
- CBTN (Children's Brain Tumor Network) and PNOC (Pediatric Neuro-Oncology Consortium)
- Published: OpenPBTA (Open Pediatric Brain Tumor Atlas)

**Correlation:** Same ecosystem as Kids First (PedcBioPortal compatible)

---

### 18. MP2PRT (Molecular Profiling to Predict Response to Treatment)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `mp2prt` |
| **S3 bucket** | `s3://gdc-mp2prt-wt-phs001965-2-open` |
| **Region** | us-east-1 |
| **License** | NIH GDS Policy |
| **Data types** | WGS (30×), Total RNA-seq, miRNA-seq, Targeted Sequencing |
| **Design** | 70 trio cases: normal + diagnosis tumor + relapse tumor |

**Hub Integration Value:**
- **Treatment resistance** molecular profiling — NCI Cancer Moonshot Initiative
- Trio design (normal → primary → relapse) enables resistance mechanism discovery
- Answers: "What genomic changes occur between primary tumor and relapse?"
- Directly relevant to drug→gene→resistance pathway modeling

---

### 19. HCMI (Human Cancer Models Initiative)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `hcmi-cmdc` |
| **S3 bucket** | `s3://gdc-hcmi-cmdc-phs001486-2-open` |
| **Region** | us-east-1 |
| **License** | NIH GDS Policy |
| **Data types** | Biospecimen + RNA-Seq Gene Expression (open) |

**Hub Integration Value:**
- Next-generation tumor-derived **organoid models** annotated with genomic + clinical data
- Focus on rare cancers, underrepresented populations, and cancers lacking precision therapy
- Requirements doc Section 2.1 lists HCMI as a GDC program (228 cases)
- Enables: "Which organoid models exist for this cancer type with this mutation?"

---

### 20. SnpEff & SnpSift Variant Annotation Databases

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `snpeff` |
| **S3 bucket** | `s3://snpeff-public` |
| **Region** | us-east-2 |
| **License** | MIT |
| **Update frequency** | Monthly |
| **Scale** | 38,000+ genomes with annotation databases |

**Hub Integration Value:**
- Comprehensive **variant effect prediction** databases (ENSEMBL, RefSeq, UCSC)
- Amino acid change prediction, splice site impact, regulatory region annotation
- Supplements the hub's `consequence_type` and `vep_impact` fields in `tcga_mutations`
- Can enrich variant nodes with predicted functional impact scores

---

### 21. CGCI (Cancer Genome Characterization Initiatives)

| Attribute | Details |
|-----------|---------|
| **RODA slug** | `cgci` |
| **S3 bucket** | `s3://gdc-cgci-phs000235-2-open` |
| **Region** | us-east-1 |
| **License** | NIH GDS Policy |
| **Data types** | Clinical, Biospecimen, RNA-Seq, miRNA-Seq (open); WGS, Targeted Seq, aligned reads (controlled) |

**Hub Integration Value:**
- **Burkitt Lymphoma** + **HIV+ Cervical Cancer** genomic characterization
- Extends cancer type coverage beyond TCGA's 33 types
- Somatic coding AND non-coding mutations in pediatric Burkitt lymphoma
- Part of GDC ecosystem (same data model, same IDs)

---

## Revised Integration Architecture (with Round 2 Datasets)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  ONCOLOGY SEMANTIC HUB — FULL RODA EXPANSION                 │
│                                                                              │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  ┌────────────┐  │
│  │ KNOWLEDGE LAYER │  │ PATIENT LAYER│  │  ML/AI LAYER  │  │ IMAGING    │  │
│  │ (Neptune Graph) │  │ (Athena Lake)│  │ (Embeddings)  │  │ (Multi-    │  │
│  │                 │  │              │  │               │  │  modal)    │  │
│  │ PrimeKG base    │  │ TCGA (33)    │  │ ESM Atlas     │  │ CAMELYON   │  │
│  │ +CIViC evidence │  │ +Beat AML    │  │ DeepDrug DPEB │  │ CHIMERA    │  │
│  │ +Genoxus ClinVar│  │ +ICGC PCAWG  │  │ Cell Painting │  │ RADIANT    │  │
│  │ +ENCODE regulat.│  │ +CPTAC-3     │  │               │  │ (path+rad) │  │
│  │ +SnpEff annot.  │  │ +Kids First  │  └───────────────┘  └────────────┘  │
│  │                 │  │ +HCMI models │                                      │
│  └─────────────────┘  │ +MP2PRT      │  ┌───────────────┐  ┌────────────┐  │
│                        │ +CGCI        │  │ POPULATION    │  │ EXPRESSION │  │
│                        │ +Exceptional │  │ CONTEXT       │  │ BASELINE   │  │
│                        │  Responders  │  │               │  │            │  │
│                        └──────────────┘  │ 1000 Genomes  │  │ CELLxGENE  │  │
│                                          │ UK Biobank    │  │ Census     │  │
│                                          │ Pan-GWAS      │  │            │  │
│                                          └───────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Coverage Against Requirements Document (Section 4)

| Requirements Doc Source | RODA Coverage | Slug |
|------------------------|---------------|------|
| **ClinVar** (variant pathogenicity) | ✅ Genoxus Annotation (harmonized + enriched) | `genoxus-annotation` |
| **COSMIC** (somatic mutations) | ⚠️ Not on RODA (download from Sanger directly) | — |
| **OncoKB** (actionability) | ✅ CIViC (similar, CC0, monthly updates) | `civic` |
| **IntOGen** (cancer drivers) | ❌ Not on RODA | — |
| **DrugBank** (drug-target) | ❌ Not on RODA (requires academic license) | — |
| **PharmGKB** (pharmacogenomics) | ❌ Not on RODA | — |
| **ChEMBL** (bioactivity) | ❌ Not on RODA | — |
| **DGIdb** (drug-gene) | ❌ Not on RODA | — |
| **STRING** (PPI) | ❌ Not on RODA | — |
| **Reactome** (pathways) | ❌ Not on RODA (but already in PrimeKG) | — |
| **DisGeNET** (gene-disease) | ❌ Not on RODA (but already in PrimeKG) | — |
| ENCODE (regulatory elements) | ✅ Full dataset on S3 | `encode-project` |
| 1000 Genomes (population freq) | ✅ Full dataset on S3 | `1000-genomes` |
| CPTAC (proteogenomics) | ✅ Phase III on S3 | `cptac-3` |
| GDC programs (TARGET, FM, HCMI) | ✅ HCMI + CGCI + Beat AML + MP2PRT on S3 | multiple |
| Pediatric cancers | ✅ Kids First (30+ studies) + RADIANT | `kids-first`, `radiant` |
| ESM/protein embeddings | ✅ ESM Atlas (6.8B proteins, us-west-2) | `biohub-esm-atlas` |
| GWAS (germline risk) | ✅ UK Biobank Pan-Ancestry | `broad-pan-ukb` |
| Digital pathology | ✅ CAMELYON + CHIMERA (us-west-2) | `camelyon`, `chimera` |

**Summary:** Of the 15 enrichment sources in your requirements doc, **6 are available on RODA** (ClinVar via Genoxus, OncoKB via CIViC, ENCODE, 1000 Genomes, CPTAC, protein embeddings). The remaining 9 (COSMIC, DrugBank, PharmGKB, ChEMBL, DGIdb, STRING, IntOGen, DisGeNET, Reactome) require direct download from their respective portals — but 5 of those 9 are already incorporated via PrimeKG.

---

## Updated Prioritized Roadmap (All 21 Datasets)

| Phase | Datasets | Theme | Effort |
|-------|----------|-------|--------|
| **1** | CIViC + Genoxus + SnpEff | Variant annotation & actionability | ~7 hrs |
| **2** | CELLxGENE + CPTAC-3 + Beat AML | Expression + proteomics + drug response | ~12 hrs |
| **3** | ICGC + 1000 Genomes + UK Biobank GWAS | Whole-genome + population context | ~14 hrs |
| **4** | ESM Atlas + DeepDrug DPEB + Cell Painting | ML-ready protein features + drug MoA | ~10 hrs |
| **5** | ENCODE + Exceptional Responders + MP2PRT | Regulatory + treatment response | ~12 hrs |
| **6** | Kids First + RADIANT + CGCI + HCMI | Pediatric + rare cancers + models | ~15 hrs |
| **7** | CAMELYON + CHIMERA | Multimodal imaging | ~8 hrs |

**Total:** ~78 hours across 7 phases (21 datasets)


---

## Appendix: RODA MCP Server Discovery Commands

These datasets were discovered using the RODA MCP server with the following queries:

```
search_datasets("cancer genomics TCGA oncology")         → 84 results
search_datasets("clinical trials biomarker")             → 42 results
search_datasets("drug sensitivity pharmacogenomics")     → 46 results
search_datasets("protein interaction network pathway")   → 163 results
find_related_datasets("civic")                           → ICGC, SnpEff, Alliance, BeatAML, Broad References
get_dataset_details("civic" | "beataml" | "icgc" | ...) → Full S3 ARNs, licenses, schemas
```

The RODA MCP server provides ongoing discoverability — as new oncology datasets are registered on RODA, they can be discovered with the same search patterns.
