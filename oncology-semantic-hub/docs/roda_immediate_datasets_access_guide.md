# RODA Datasets — Integration Guide for Oncology Semantic Hub

> **Date:** 30 July 2026 | **For:** Coding Agent Teammates  
> **Goal:** Enrich the Oncology Semantic Hub with datasets from the AWS Registry of Open Data (RODA)  
> **Tools available:** RODA MCP Server (discovery/preview/sample), OLS MCP Server (terminology alignment), Athena (query), Neptune (graph)

---

## ⚠️ Key Design Principle: Query-in-Place vs. Ingest

**Before integrating each dataset, you MUST make and record a decision:**

> **Can this dataset be queried directly from RODA's S3 bucket (no copy)?**  
> Or does it require ETL into our account?

### Decision Criteria

| Query Directly from RODA | Requires ETL into Our Account |
|--------------------------|-------------------------------|
| Already Parquet/ORC format | Raw TSV/CSV that needs conversion |
| Hive-partitioned (efficient scans) | Flat file dump (full-scan every query) |
| Schema is stable and documented | Needs reshaping / joining with other data |
| Small enough for per-query scan cost | Large enough that repeated scans are expensive |
| No enrichment/transformation needed | Needs computed columns, joins, or filtering |

**If the dataset is already optimized (Parquet + partitioned), point Athena at it directly. If it needs any transformation, bring it into our account.**

### Record Every Decision

For each dataset, log:
```
Dataset: [name]
Decision: DIRECT_QUERY | INGEST
Rationale: [why]
Access method: [Athena EXTERNAL TABLE | S3 copy + Parquet convert | Neptune ETL]
Join key to hub: [field → hub field]
Terminology mapping needed: [yes/no, which OLS ontology]
Date: [when integrated]
```

---

## RODA MCP Server — Discovery Workflow

The RODA MCP server lets you explore any dataset **before committing to integration**:

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `search_datasets(query)` | Find datasets by topic |
| 2 | `preview_dataset(slug)` | See S3 bucket structure — file formats, sizes, partitioning |
| 3 | `sample_dataset(slug, file_key)` | Pull first 100KB — inspect actual schema, columns, sample rows |
| 4 | **Make your decision** | DIRECT_QUERY or INGEST? Record it. |
| 5 | Integrate | Either `CREATE EXTERNAL TABLE` or run ETL |

No AWS credentials needed for any RODA bucket — all use `--no-sign-request`.

---

## Immediate Datasets (6)

### 1. CIViC (Clinical Interpretation of Variants in Cancer)

```
Bucket:   s3://civic-aws-opendata
Region:   us-west-2
License:  CC0 (public domain)
Format:   TSV (monthly dumps), Hive-partitioned by date
Updated:  1st of each month
```

**What it contains:** Variant-level clinical evidence — gene, variant, disease, drugs, evidence level (A/B/C/D/E), clinical significance (sensitivity/resistance/diagnostic/prognostic)

**Sample columns (ClinicalEvidenceSummaries.tsv):**
```
gene | variant | disease | doid | drugs | evidence_type | evidence_level | clinical_significance
BRAF | V600E   | Melanoma | 1909 | Vemurafenib | Predictive | A | Sensitivity/Response
```

**Join keys:** `gene` → `gene_protein.name` | `doid` → MONDO via OLS | `drugs` → `drug.name`

**File layout:**
```
ClinicalEvidenceSummaries/date=01-Jul-2024/ClinicalEvidenceSummaries.tsv  (~4MB)
AssertionSummaries/date=01-Jul-2024/AssertionSummaries.tsv                (~60KB)
VariantSummaries/date=01-Jul-2024/VariantSummaries.tsv                    (~500KB)
GeneSummaries/date=01-Jul-2024/GeneSummaries.tsv                          (~80KB)
```

---

### 2. Genoxus Annotation (Harmonized ClinVar)

```
Bucket:   s3://genoxus-annotation-release
Region:   us-west-2
License:  CC-BY 4.0
Format:   Parquet, Hive-partitioned by GRCh/chr/bp (1MB windows)
Updated:  June 2026
```

**What it contains:** ClinVar variants (SNVs, INDELs, CNVs, SVs) with standardized disease terminology and pathogenicity classifications.

**File layout (already Athena-native):**
```
Genoxus-Annotation/
  GRCh=38/
    chr=17/
      bp=43000001-44000000/clinvar.parquet   ← BRCA1 region
```

**Join keys:** chr:pos:ref:alt → `tcga_mutations` positional match

**Note:** This is the fastest integration — `CREATE EXTERNAL TABLE` pointing at their bucket. Zero ETL.

---

### 3. SnpEff (Variant Effect Prediction)

```
Bucket:   s3://snpeff-public
Region:   us-east-2
License:  MIT
Format:   gzipped TSV (dbNSFP — 34GB compressed)
Updated:  Monthly
```

**What it contains:** Pathogenicity prediction scores from 30+ algorithms (SIFT, PolyPhen2, CADD, REVEL, etc.) for every possible missense variant.

**Note:** Large dataset (34GB compressed, ~200GB uncompressed). Consider subsetting to cancer-relevant genes.

**Join keys:** chr:pos:ref:alt → `tcga_mutations`

---

### 4. Beat AML 1.0

```
Bucket:   s3://gdc-beataml1-cohort-phs001657-2-open
Region:   us-east-1
License:  NIH GDS (open access)
Format:   Per-sample TSV (STAR gene counts, ~4MB each)
```

**What it contains:** RNA-Seq gene expression (TPM, FPKM, raw counts) for AML patients. GENCODE v36.

**Sample columns (augmented_star_gene_counts.tsv):**
```
gene_id             | gene_name | gene_type      | tpm_unstranded | fpkm_unstranded
ENSG00000000938.13  | FGR       | protein_coding | 301.99         | 83.81
```

**Join keys:** `gene_name` → `gene_protein.name` (Hugo Symbol)

**Note:** Per-sample files — needs aggregation + case_id mapping via GDC API to link to clinical/mutation data.

---

### 5. CPTAC-3 (Proteogenomics)

```
Bucket:   s3://gdc-cptac-phs001287-2-open
Region:   us-east-1
License:  NIH GDS (open access)
Format:   Same as BeatAML (per-sample GDC gene counts)
```

**What it contains:** RNA-Seq expression from proteogenomically-characterized tumors (clear cell RCC, breast, colon, etc.)

---

### 6. CCLE (Cancer Cell Line Encyclopedia)

```
Bucket:   s3://gdc-ccle-2-open
Region:   us-east-1
License:  NIH GDS (open access)
Format:   GDC-style per-sample files (RNA-Seq + mutations)
```

**What it contains:** 1,000+ cancer cell lines with expression and mutation data. The experimental validation layer — "which cell line models this genotype?"

---

## Terminology Alignment (OLS MCP Server)

These datasets use different ontologies. The OLS MCP server resolves mismatches at query time:

| From (dataset) | To (hub) | OLS approach |
|---------------|----------|-------------|
| DOID (CIViC diseases) | MONDO (Neptune) | `search_terms("DOID:1909", ontology="mondo")` |
| Free-text drug names | DrugBank/ChEBI (Neptune) | `search_terms("Trastuzumab", ontology="chebi")` |
| Ensembl Gene ID (BeatAML) | Hugo Symbol (Neptune) | `search_terms("ENSG00000157764", ontology="hgnc")` |
| GRCh37/38 coordinates | Both | Positional match, no mapping needed |

The OLS server ensures data from different sources lands on the same ontology terms in the hub — regardless of what vocabulary the source uses.

---

## Metadata-First Integration Pattern

For each dataset, consider loading **only metadata into Neptune** (lightweight), then **querying detail on-demand from Athena**:

1. **Neptune enrichment** — add properties to existing nodes (e.g., `gene_protein.has_civic_evidence = true`)
2. **Athena EXTERNAL TABLE or internal table** — full detail data accessible when the agent needs it
3. **Agent flow** — discover via Neptune graph traversal → fetch specifics from Athena

This avoids loading millions of rows into Neptune when only the relationships and discovery flags matter for graph traversal.

---

## Access Commands (all no-sign-request)

```bash
# List contents
aws s3 ls s3://civic-aws-opendata/ --no-sign-request
aws s3 ls s3://genoxus-annotation-release/ --no-sign-request
aws s3 ls s3://snpeff-public/ --no-sign-request
aws s3 ls s3://gdc-beataml1-cohort-phs001657-2-open/ --no-sign-request

# Download a single file for inspection
aws s3 cp s3://civic-aws-opendata/ClinicalEvidenceSummaries/date=01-Jul-2024/ClinicalEvidenceSummaries.tsv . --no-sign-request

# For Genoxus — don't download, just point Athena at it
```

---

## What to Do Next

1. Pick one dataset
2. Use RODA MCP to `preview_dataset` and `sample_dataset`
3. Inspect the schema — what columns exist, what's the join key to the hub
4. Decide: **DIRECT_QUERY** or **INGEST**
5. Record the decision with rationale
6. Integrate (Athena table or Neptune enrichment)
7. Test with a sample agent query
8. Move to the next dataset

**Start with Genoxus** — it's the fastest (zero ETL, already Parquet, same region). Then CIViC (small TSV, high value). Then the GDC datasets (more ETL effort).
