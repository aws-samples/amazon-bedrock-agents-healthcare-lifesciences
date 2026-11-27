# Data Sources: Comparison & Correlation Potential

> **Purpose:** Understand how GDC, TCGA, cBioPortal, and other sources relate to each other, what's unique to each, and whether they can be correlated at the patient level.  
> **Last updated:** May 11, 2026

---

## How the Sources Relate

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        NCI Genomic Data Commons (GDC)                    │
│                     The authoritative data repository                    │
│                                                                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│   │  TCGA    │  │  TARGET  │  │  CPTAC   │  │   FM     │  │  HCMI  │  │
│   │ 11,315   │  │  6,542   │  │  1,526   │  │ 18,004   │  │   228  │  │
│   │ 33 types │  │ Pediatric│  │ Proteo-  │  │ Clinical │  │Organoid│  │
│   │ Bulk omics│  │ cancers  │  │ genomics │  │ panels   │  │+scRNA  │  │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
         │                                                         
         │ Same patients, processed differently                    
         ▼                                                         
┌─────────────────────────────────────────────────────────────────────────┐
│                           cBioPortal (MSK)                               │
│                  Analysis & visualization layer                          │
│                                                                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│   │TCGA (all)│  │  TARGET  │  │ MSK-IMPACT   │  │  AACR GENIE       │  │
│   │processed │  │processed │  │ 18K+ cases   │  │  100K+ cases      │  │
│   │summaries │  │summaries │  │ NOT in GDC   │  │  19 institutions  │  │
│   └──────────┘  └──────────┘  └──────────────┘  └───────────────────┘  │
│                                                                         │
│   + 400 other published studies (METABRIC, institutional cohorts, etc.) │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Source-by-Source Comparison

### GDC (Genomic Data Commons)

| Attribute | Details |
|-----------|---------|
| **Role** | NCI's authoritative data repository — source of truth |
| **Total cases** | ~86,000 across 78 projects |
| **Programs** | TCGA, TARGET, CPTAC, FM, HCMI, MMRF, BEATAML, CGCI, and more |
| **Data types** | Raw sequencing (BAM/CRAM), somatic mutations (MAF/VCF), gene expression (counts), CNV, methylation, protein (RPPA), scRNA-seq, clinical |
| **Unique to GDC** | Raw files, methylation arrays, scRNA-seq, controlled-access germline, harmonized pipeline (all GRCh38) |
| **API** | REST + GraphQL, paginated, open-access + controlled-access tiers |
| **Gene IDs** | Ensembl (ENSG) |
| **Disease IDs** | ICD-O-3 morphology codes |
| **Patient IDs** | UUID + TCGA barcodes (submitter_id) |

### TCGA (The Cancer Genome Atlas)

| Attribute | Details |
|-----------|---------|
| **Role** | A completed research program (2006–2017) hosted within GDC |
| **Total cases** | 11,315 across 33 cancer types |
| **Status** | No new data. Fully characterized. The "gold standard" for pan-cancer analysis. |
| **Data types** | Bulk WES, bulk RNA-seq, methylation (450K), RPPA, miRNA, clinical outcomes |
| **NOT available** | Single-cell, spatial omics, WGS (for most), longitudinal follow-up |
| **Why it matters** | Largest uniformly-processed multi-cancer cohort. Every patient has matched normal. Extensively published. |

### cBioPortal

| Attribute | Details |
|-----------|---------|
| **Role** | Analysis portal — pre-processed, ready-to-query summaries |
| **Total studies** | 400+ (including all TCGA) |
| **Unique data** | MSK-IMPACT (18K clinical cases), AACR GENIE (100K+ multi-institution), METABRIC (2,509 breast), institutional cohorts |
| **Data types** | Discrete CNA (GISTIC), expression z-scores, mutations (MAF), structural variants, clinical timelines, drug response |
| **Unique features** | OncoKB actionability levels, survival analysis, OncoPrint visualization, gene panels |
| **API** | Swagger/OpenAPI, no auth for public studies |
| **Gene IDs** | Hugo Symbol + Entrez |
| **Disease IDs** | OncoTree codes |
| **Patient IDs** | Study-specific sample IDs |

---


---

## AWS Open Data Registry: TCGA on S3

TCGA data is also available as an AWS Open Dataset at `s3://tcga-2-open` (us-east-1), providing direct S3 access to the same GDC files without API pagination or rate limits.

**Access:** `aws s3 ls --no-sign-request s3://tcga-2-open/`

### Comparison: S3 Bucket vs GDC API vs cBioPortal

| Data Type | AWS S3 (`tcga-2-open`) | GDC API | cBioPortal API | What We Used |
|-----------|:---:|:---:|:---:|---|
| Somatic Mutations (MAF) | ✅ Full MAF files | ✅ Pre-computed `/ssm_occurrences` | ✅ Processed MAF | GDC API (slow — 5hrs) |
| Gene Expression (counts) | ✅ Full genome-wide STAR counts | ✅ `/gene_expression/values` (batch) | ✅ Z-scores (limited genes) | cBioPortal (10 genes only) |
| Copy Number Segments | ✅ Full resolution | ✅ `/cnv_occurrences` | ✅ Discrete GISTIC | cBioPortal (discrete) |
| Clinical Supplement | ✅ BCR XML/TSV | ✅ `/cases` JSON (structured) | ✅ Clinical attributes | GDC API (best) |
| Methylation | ✅ Beta values | ✅ File download only | ❌ Not available | Not used |
| miRNA Expression | ✅ Isoform + gene level | ✅ File download | ❌ Not available | Not used |
| Aligned Reads (BAM) | ❌ Controlled bucket only | ❌ Controlled access | ❌ Not available | Not used |

### Performance Comparison

| Method | Mutations (33 projects) | Expression (genome-wide) | Advantage |
|--------|------------------------|--------------------------|-----------|
| **AWS S3 direct** | ~10 min (bulk download MAFs) | ~30 min (download count files) | Fastest. No pagination. No rate limits. Same-region to our S3 bucket. |
| **GDC API** | ~5 hours (paginated JSON) | Hours (batch of 50 cases × 50 genes) | Structured, filterable, but slow at scale. |
| **cBioPortal API** | ~15 min (pre-processed) | ~15 min (limited to specific genes) | Fast for summaries, but limited scope. |

### Lesson Learned

Our Sprint 1 mutation extraction took **5 hours** via the GDC API because we paginated through `/ssm_occurrences` one page at a time. The same data is available on S3 as pre-built MAF files that could be downloaded in **~10 minutes** and converted to Parquet locally or on a Lambda.

### Recommended Approach for Future Data Loads

| Data | Best Source | Why |
|------|------------|-----|
| Somatic mutations (full MAF) | **AWS S3 `tcga-2-open`** | Bulk download, no pagination, all MAF columns |
| Gene expression (genome-wide) | **AWS S3 `tcga-2-open`** | Full 60K genes, not limited to 10 |
| Clinical metadata | **GDC API `/cases`** | Structured JSON, easy to flatten, filterable |
| Discrete CNA (GISTIC) | **cBioPortal API** | Pre-processed gene-level, fast |
| Copy number segments | **AWS S3 `tcga-2-open`** | Full resolution, all chromosomes |
| Non-TCGA studies (MSK-IMPACT, GENIE) | **cBioPortal API** | Only source for these cohorts |

## Can We Correlate at the Patient Level?

### Same patients across sources:

| Source A | Source B | Correlation Key | Same Patients? |
|----------|----------|----------------|----------------|
| **GDC TCGA** | **cBioPortal TCGA** | TCGA barcode (e.g., TCGA-A2-A04P) | ✅ Yes — identical patients, different processing |
| **GDC TCGA** | **cBioPortal MSK-IMPACT** | None | ❌ No — completely different patient cohorts |
| **GDC TCGA** | **GDC TARGET** | None | ❌ No — different programs, different patients |
| **GDC TCGA** | **ClinVar** | Gene-level only (not patient-level) | ⚠️ Gene overlap, not patient overlap |
| **GDC TCGA** | **COSMIC** | Mutation-level (chr:pos:ref:alt) | ⚠️ Same mutations may appear, but different patients |
| **cBioPortal GENIE** | **cBioPortal MSK-IMPACT** | MSK-IMPACT is a subset of GENIE | ✅ Partial overlap |

### What this means for the semantic hub:

- **TCGA patients** can be correlated across GDC and cBioPortal using the TCGA barcode — we already do this (same 11,428 patients, different data views)
- **MSK-IMPACT and GENIE** are separate patient cohorts — they add breadth (more patients, clinical setting) but can't be linked to TCGA patients
- **ClinVar and COSMIC** correlate at the **variant/gene level**, not patient level — they tell us "this mutation is pathogenic" regardless of which patient has it
- **PrimeKG** correlates at the **entity level** — genes, diseases, drugs, pathways are shared concepts across all patient cohorts

---

## Additional Sources That Could Enrich the Hub

### Patient-Level Data (new cohorts)

| Source | Cases | What It Adds | Correlation to TCGA |
|--------|-------|-------------|---------------------|
| **MSK-IMPACT** (via cBioPortal) | 18,000+ | Real clinical sequencing, treatment outcomes, 468-gene panel | ❌ Different patients, but same genes |
| **AACR GENIE** (via cBioPortal) | 100,000+ | Multi-institution clinical genomics, diverse populations | ❌ Different patients |
| **METABRIC** (via cBioPortal) | 2,509 | Deep breast cancer profiling, long follow-up | ❌ Different patients |
| **GDC TARGET** | 6,542 | Pediatric cancers (AML, ALL, neuroblastoma, Wilms) | ❌ Different patients |
| **GDC CPTAC** | 1,526 | Proteomics + genomics (protein-level validation) | ⚠️ Some overlap with TCGA cases |

### Gene/Variant-Level Enrichment (no patient data)

| Source | What It Adds | Correlation Level |
|--------|-------------|-------------------|
| **ClinVar** | Variant pathogenicity (already integrated — 6,286 genes) | Gene + variant |
| **COSMIC** | Somatic mutation frequencies across cancers (74 Tier 1 genes done) | Gene + variant |
| **PharmGKB** | Pharmacogenomics — drug response by genotype | Gene + drug |
| **OncoKB** | Actionability levels (Level 1-4) for mutations | Gene + variant + drug |
| **CIViC** | Clinical interpretation of variants (community-curated) | Gene + variant + disease |
| **IntOGen** | Cancer driver gene identification (statistical) | Gene |

### Knowledge/Ontology Enrichment

| Source | What It Adds | Correlation Level |
|--------|-------------|-------------------|
| **EBI OLS** (200+ ontologies) | Synonym resolution, hierarchy traversal, cross-references | Ontology |
| **UMLS Metathesaurus** | Cross-references between MONDO, ICD-10, SNOMED, MeSH | Disease |
| **UniProt** | Protein structure, domains, post-translational modifications | Gene/protein |
| **Human Cell Atlas / CellxGene** | Single-cell expression atlases (50M+ cells) | Cell type + gene |
| **TCIA** (Cancer Imaging Archive) | Radiology images linked to TCGA cases | ✅ Same TCGA patients |
| **GEO** (Gene Expression Omnibus) | Thousands of expression studies | Gene (not patient-linked) |

### Single-Cell & Spatial (emerging)

| Source | What It Adds | Availability |
|--------|-------------|-------------|
| **GDC scRNA-seq** (HCMI, CPTAC-3) | Per-cell expression for GDC cases | API available (`/scrna_seq/gene_expression`) |
| **CellxGene** (CZI) | 50M+ cells, hundreds of cancer studies | Python SDK (`cellxgene-census`) |
| **10x Genomics datasets** | Spatial transcriptomics reference data | Public downloads |
| **Human Tumor Atlas Network (HTAN)** | Multi-modal single-cell + spatial | Via GDC (limited) |

---

### Deep Dive: Single-Cell & Spatial Omics Sources

#### HTAN (Human Tumor Atlas Network)

| Attribute | Details |
|-----------|---------|
| **What it is** | NCI Cancer Moonshot initiative — 3D atlases of tumor evolution from pre-cancer to advanced disease |
| **Data types** | scRNA-seq, scATAC-seq, CODEX/CyCIF spatial proteomics, MERFISH spatial transcriptomics, H&E imaging, bulk WES/WGS |
| **Cancer types** | Breast, colon, lung, pancreas, brain (glioma), melanoma, and more |
| **Scale** | 10+ research centers, hundreds of thousands of cells per atlas |
| **Access** | HTAN Data Portal (`humantumoratlas.org`), data hosted on Synapse + GDC + IDC |
| **API/Download** | Synapse Python client, CDS (Cancer Data Service), some data via GDC |
| **Gene IDs** | Ensembl |
| **Unique value** | Spatial context — where cells are relative to each other in the tumor microenvironment. Tracks tumor evolution over time (pre-malignant → invasive → metastatic). |
| **Correlation to TCGA** | ❌ Different patients. Same cancer types but at much higher resolution (single-cell vs bulk). Some HTAN centers use TCGA-adjacent tissue banks. |
| **Integration approach** | Gene-level: HTAN cell-type markers → PrimeKG gene nodes. Disease-level: HTAN cancer types → MONDO disease nodes. Spatial: new node type `cell_type` with tissue localization properties. |

#### CancerSCEM (Cancer Single-Cell Expression Map)

| Attribute | Details |
|-----------|---------|
| **What it is** | Database of uniformly processed scRNA-seq data across human cancers (NGDC/CNCB, China) |
| **URL** | `https://ngdc.cncb.ac.cn/cancerscem` |
| **Data types** | scRNA-seq expression matrices, cell type annotations, marker genes, differentially expressed genes |
| **Cancer types** | 20+ cancer types, 208+ samples, 28+ studies (v1.0); expanded in v2.0 |
| **Scale** | Millions of cells with uniform processing (Seurat/Scanpy pipeline) |
| **Access** | Web portal with download links, no formal API |
| **Gene IDs** | Gene symbols (Hugo) |
| **Unique value** | Uniform reprocessing of published scRNA-seq datasets — comparable across studies. Cell state annotations (proliferating, quiescent, EMT, etc.). Pre-computed marker genes per cell type per cancer. |
| **Correlation to TCGA** | ❌ Different patients. Gene-level overlap only. |
| **Integration approach** | Cell-type marker genes → PrimeKG gene nodes (add `cell_type_marker` property or edges). Cancer-type cell composition → disease node properties. |

#### CancerSEA (Cancer Single-Cell State Atlas)

| Attribute | Details |
|-----------|---------|
| **What it is** | Atlas of 14 functional states of cancer cells at single-cell resolution |
| **URL** | `https://biocc.hrbmu.edu.cn/CancerSEA/` |
| **Functional states** | Stemness, invasion, metastasis, proliferation, EMT, angiogenesis, apoptosis, cell cycle, differentiation, DNA damage, DNA repair, hypoxia, inflammation, quiescence |
| **Scale** | 41,900 cancer single cells, 25 cancer types |
| **Unique value** | Maps genes to functional states — e.g., "TP53 is associated with DNA damage state in breast cancer cells". This is a gene→function→cancer type relationship not in PrimeKG. |
| **Integration approach** | Add `functional_state` node type with edges to genes. Or add as gene properties: `cancer_states: [DNA_damage, apoptosis]`. |

#### 10x Genomics Spatial Datasets

| Attribute | Details |
|-----------|---------|
| **What it is** | Reference spatial transcriptomics datasets from 10x Genomics (Visium, Xenium) |
| **URL** | `https://www.10xgenomics.com/datasets` |
| **Data types** | Visium (spot-level, ~55µm resolution, whole transcriptome), Xenium (subcellular, 300+ gene panels) |
| **Cancer types** | Breast, brain, colon, lung, ovarian, prostate, melanoma |
| **Scale** | Dozens of reference datasets, each with thousands of spatial spots/cells |
| **Access** | Direct download (no API), `.h5ad` and `.h5` formats |
| **Gene IDs** | Gene symbols (Hugo) |
| **Unique value** | Spatial coordinates — gene expression mapped to physical location in tissue. Reveals tumor-stroma boundaries, immune infiltration patterns, spatial heterogeneity. |
| **Correlation to TCGA** | ❌ Different patients. Gene-level and tissue-type overlap only. |
| **Integration approach** | Spatial gene signatures → PrimeKG gene nodes. Tissue regions → anatomy nodes. Could add `spatial_marker` property to genes that show spatial patterns. |

---

### Summary: Single-Cell & Spatial Integration Strategy

| Source | Correlation Level | What It Adds to the Hub | Priority |
|--------|------------------|------------------------|----------|
| **HTAN** | Gene + disease + cell type | Tumor evolution, spatial context, cell-type composition | P1 (richest, NCI-backed) |
| **CancerSCEM** | Gene + cell type | Uniform cell-type markers across 20+ cancers | P2 (pre-processed, easy) |
| **CancerSEA** | Gene + functional state | 14 cancer cell states mapped to genes | P2 (unique functional layer) |
| **10x Spatial** | Gene + spatial location | Spatial gene expression patterns | P3 (reference data, not patient cohorts) |
| **CellxGene** | Gene + cell type | 50M+ cells, largest single-cell resource | P1 (scale, API available) |

**Key insight:** None of these correlate at the patient level with TCGA. They correlate at the **gene level** (same genes, different resolution) and **disease level** (same cancer types, different patients). The integration value is adding cell-type and spatial context to existing gene nodes — e.g., "TP53 is a marker of the DNA-damage state in breast cancer stem cells" or "EGFR is spatially enriched at the tumor-stroma boundary in GBM."

---

## Correlation Strategy for the Semantic Hub

```
PATIENT-LEVEL CORRELATION (same individuals):
  TCGA barcode links: GDC ↔ cBioPortal ↔ TCIA (imaging)
  
GENE-LEVEL CORRELATION (same biological entities):
  Entrez Gene ID links: PrimeKG ↔ ClinVar ↔ COSMIC ↔ OncoKB ↔ PharmGKB
  
DISEASE-LEVEL CORRELATION (same conditions):
  MONDO ID links: PrimeKG diseases ↔ TCGA projects ↔ ICD-10 ↔ SNOMED
  
VARIANT-LEVEL CORRELATION (same mutations):
  chr:pos:ref:alt links: GDC mutations ↔ ClinVar ↔ COSMIC ↔ CIViC
```

### What's already correlated in our hub today:

| Link | How | Count |
|------|-----|-------|
| TCGA patients ↔ PrimeKG diseases | `case_has_diagnosis` edges via MONDO mapping | 11,428 |
| TCGA mutations ↔ PrimeKG genes | Hugo Symbol join (Athena ↔ Neptune) | 33 projects |
| ClinVar pathogenicity ↔ PrimeKG genes | `clinvar_pathogenic_count` property | 6,286 genes |
| COSMIC drivers ↔ PrimeKG genes | `cosmic_tier` property | 74 genes |
| MONDO diseases ↔ ICD-10 codes | `icd10` property on disease nodes | 500 diseases |

### What could be added next (by correlation type):

| Priority | Source | Correlation | Effort |
|----------|--------|-------------|--------|
| P0 | OncoKB | Variant → actionability level (Level 1 = FDA-approved) | 2 hrs |
| P1 | MSK-IMPACT (cBioPortal) | New patient cohort (clinical, not research) | 3 hrs |
| P1 | TCIA | Imaging for same TCGA patients (TCGA barcode link) | 4 hrs |
| P2 | CellxGene | Single-cell expression atlas (gene-level, not patient) | 4 hrs |
| P2 | PharmGKB | Drug-gene-variant pharmacogenomics | 2 hrs |
| P3 | HTAN spatial | Spatial transcriptomics (emerging, limited) | 8 hrs |
