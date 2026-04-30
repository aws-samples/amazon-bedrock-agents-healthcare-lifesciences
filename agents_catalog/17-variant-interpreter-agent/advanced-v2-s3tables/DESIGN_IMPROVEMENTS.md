# Design Improvements — VEP Annotation at Scale

## What VEP Does

Ensembl's Variant Effect Predictor (VEP) takes a genomic variant (e.g. chr17:41276045 A>G) and produces functional annotations. It performs five categories of work:

### 1. Transcript Overlap Lookup (~40% of work)
Positional lookup against the cache database to find which gene transcripts overlap the variant position. The cache contains pre-indexed transcript models for every known gene. This is a pure lookup — same input always produces same output.

### 2. Consequence Calculation (~25% of work)
Determines the functional effect: missense, synonymous, frameshift, stop_gained, splice_donor, intron_variant, etc. This requires knowing the reading frame of the overlapping transcript and computing whether the variant changes the amino acid sequence. This is computation, not lookup — but it's deterministic given the same variant + transcript.

### 3. HGVS Notation Generation (~15% of work)
Produces standardized nomenclature like `ENST00000357654:c.1799T>A` (coding DNA) and `p.Val600Glu` (protein). Requires codon translation and position mapping within the transcript.

### 4. Distance and Region Annotation (~10% of work)
Calculates distance to nearest gene for intergenic variants, identifies regulatory regions, and flags splice site proximity. Mostly positional arithmetic.

### 5. Plugin-Based Predictions (~10% of work)
Optional plugins like SIFT, PolyPhen, CADD that predict pathogenicity scores. These are additional lookups against pre-computed score databases.

**Key insight:** For a given variant (chrom + pos + ref + alt) against a fixed cache version, VEP always produces the exact same annotation. The output is deterministic.

---

## The Duplication Problem

### Current Design: Per-Sample VEP

```
Patient NA21135.vcf → VEP → annotated NA21135.ann.vcf → S3 Tables
Patient NA21137.vcf → VEP → annotated NA21137.ann.vcf → S3 Tables
Patient NA21141.vcf → VEP → annotated NA21141.ann.vcf → S3 Tables
...
Patient NA21999.vcf → VEP → annotated NA21999.ann.vcf → S3 Tables
```

Each VCF from `s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA*.hard-filtered.vcf.gz` contains ~4-5 million variants per sample. Across a 2000-sample cohort:

- **Total VEP runs:** 2000 (one per sample, ~1 hour each = 2000 compute-hours)
- **Total variants annotated:** ~8-10 billion
- **Unique variant sites:** ~50-100 million (most variants are shared across samples)
- **Duplication factor:** ~100x — the same variant is annotated 100 times on average

### Cost Impact

At ~$0.50-2.00 per HealthOmics VEP run:
- Current: 2000 runs × $1.00 = **$2,000**
- Optimized: ~50 runs (batched unique sites) × $1.00 = **$50**

Storage duplication in S3 Tables is also significant — the annotation columns (gene, consequence, HGVS, etc.) are identical for shared variants but stored per-sample.

---

## Proposed Improvement: Annotate-Once Architecture

### Overview

Instead of running VEP 2000 times (once per sample), run it once on the deduplicated set of unique variant sites across the entire cohort. The existing VEP workflow (`workflow_definition_5035092`) is reused as-is for the annotation step — only the input changes from a per-sample VCF to a sites-only VCF.

### Two-Workflow Design

**Workflow 1: EXTRACT_UNIQUE_SITES (new — needs to be built)**

A Nextflow workflow that reads all per-sample VCFs and produces a single sites-only VCF containing every unique (chrom, pos, ref, alt) tuple. Runs on HealthOmics with parallelism by chromosome.

**Workflow 2: ENSEMBLVEP (existing — `workflow_definition_5035092`)**

The proven VEP workflow, unchanged. Takes the sites-only VCF as input instead of a per-sample VCF. Produces the annotation lookup table.

### Step 1: Extract Unique Sites (HealthOmics Workflow)

The approach does NOT merge VCFs into a multi-sample VCF (which is memory-intensive and produces a huge file). Instead, it streams through each VCF extracting only the 4-column site key, deduplicates per chromosome, and outputs a minimal sites-only VCF.

```nextflow
nextflow.enable.dsl = 2

params.vcf_list = null       // S3 path to file listing all VCF S3 URIs (one per line)
params.chromosomes = "chr1,chr2,chr3,chr4,chr5,chr6,chr7,chr8,chr9,chr10,chr11,chr12,chr13,chr14,chr15,chr16,chr17,chr18,chr19,chr20,chr21,chr22,chrX,chrY"

process EXTRACT_SITES_PER_CHROM {
    tag "$chrom"
    container 'biocontainers/bcftools:1.17'
    cpus 2
    memory '4 GB'

    input:
    val chrom
    path vcf_list

    output:
    path "${chrom}_sites.vcf.gz", emit: sites_vcf

    script:
    """
    set -eu

    # Extract sites from all VCFs for this chromosome, deduplicate
    echo "##fileformat=VCFv4.2" > header.txt
    echo "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO" >> header.txt

    while IFS= read -r vcf_path; do
        bcftools query -r ${chrom} -f '%CHROM\\t%POS\\t.\\t%REF\\t%ALT\\t.\\t.\\t.\\n' "\$vcf_path" 2>/dev/null || true
    done < ${vcf_list} | \
    sort -k1,1V -k2,2n -k4,4 -k5,5 | uniq | \
    cat header.txt - | bgzip > ${chrom}_sites.vcf.gz

    tabix -p vcf ${chrom}_sites.vcf.gz
    """
}

process CONCAT_SITES {
    container 'biocontainers/bcftools:1.17'
    cpus 2
    memory '4 GB'

    input:
    path site_vcfs

    output:
    path "all_unique_sites.vcf.gz", emit: merged

    script:
    """
    set -eu
    bcftools concat ${site_vcfs} -O z -o all_unique_sites.vcf.gz
    tabix -p vcf all_unique_sites.vcf.gz
    """
}

workflow {
    chromosomes = Channel.from(params.chromosomes.split(','))
    vcf_list = file(params.vcf_list, checkIfExists: true)

    EXTRACT_SITES_PER_CHROM(chromosomes, vcf_list)
    CONCAT_SITES(EXTRACT_SITES_PER_CHROM.out.sites_vcf.collect())
}
```

**Resource profile:** 24 parallel tasks (one per chromosome) × 2 CPUs / 4 GB each. Each task streams through 2000 VCFs reading only the target chromosome region — I/O bound, not memory bound.

**Input:** A text file listing S3 paths to all per-sample VCFs:
```
s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21135.hard-filtered.vcf.gz
s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21137.hard-filtered.vcf.gz
...
```

**Output:** `all_unique_sites.vcf.gz` — a single VCF with ~50-100M unique variant sites, no genotype data.

### Step 2: Annotate Unique Sites (Existing VEP Workflow)

Run the existing `workflow_definition_5035092` with:
```json
{
    "id": "cohort_annotations",
    "vcf": "s3://output-bucket/all_unique_sites.vcf.gz",
    "vep_cache": "s3://genomics-vep-cache2-942514891246-us-west-2/cache/",
    "vep_cache_version": "113",
    "vep_genome": "GRCh38",
    "vep_species": "homo_sapiens",
    "ecr_registry": "942514891246.dkr.ecr.us-west-2.amazonaws.com"
}
```

This produces `cohort_annotations.ann.vcf.gz` — the complete annotation lookup for every variant seen in the cohort.

### Step 3: Load into S3 Tables (Two Tables)

```
variant_calls table:
  sample_name | chrom | pos | ref | alt | qual | filter | genotype
  (loaded from raw per-sample VCFs — no VEP needed)

variant_annotations table:
  chrom | pos | ref | alt | gene | consequence | impact | hgvs_c | hgvs_p | sift | polyphen
  (loaded once from cohort_annotations.ann.vcf.gz)
```

### Step 4: Query with JOIN

```sql
SELECT v.sample_name, v.chrom, v.pos, v.ref, v.alt,
       a.gene, a.consequence, a.impact, a.hgvs_p
FROM variant_db_3.variant_calls v
JOIN variant_db_3.variant_annotations a
    ON v.chrom = a.chrom AND v.pos = a.pos AND v.ref = a.ref AND v.alt = a.alt
WHERE v.sample_name = 'NA21135'
  AND a.impact = 'HIGH'
```

### How to Generate the VCF List

For the 1000 Genomes DRAGEN data:
```bash
aws s3 ls s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/ \
    | grep 'hard-filtered.vcf.gz$' \
    | awk '{print "s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/" $4}' \
    > vcf_list.txt

# Upload to S3 for the workflow
aws s3 cp vcf_list.txt s3://genomics-vcf-input-v3-942514891246-us-west-2/cohort/vcf_list.txt
```

---

## Incremental Updates (New Samples)

When new samples arrive after the initial cohort annotation:

1. Load raw variants from new sample into `variant_calls` table
2. Query for novel sites not yet in `variant_annotations`:
   ```sql
   SELECT DISTINCT v.chrom, v.pos, v.ref, v.alt
   FROM variant_db_3.variant_calls v
   LEFT JOIN variant_db_3.variant_annotations a
       ON v.chrom = a.chrom AND v.pos = a.pos AND v.ref = a.ref AND v.alt = a.alt
   WHERE v.sample_name = 'NEW_SAMPLE'
     AND a.chrom IS NULL
   ```
3. Export novel sites to VCF
4. Run existing VEP workflow (`workflow_definition_5035092`) on novel sites only
5. Append results to `variant_annotations` table

For a new sample in an established cohort, typically <5% of variants are truly novel — so VEP runs on a tiny fraction.

---

## Revised Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    INITIAL COHORT SETUP                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  s3://1000genomes-dragen/.../NA*.hard-filtered.vcf.gz           │
│                          │                                      │
│           ┌──────────────┼──────────────┐                       │
│           │              │              │                        │
│           ▼              ▼              ▼                        │
│  ┌─────────────┐  ┌───────────────────────────────┐            │
│  │ Load raw    │  │ Extract Unique Sites Workflow  │            │
│  │ variants    │  │ (NEW - per chromosome)         │            │
│  │ to S3 Tables│  │ bcftools query | sort | uniq   │            │
│  └──────┬──────┘  └───────────────┬───────────────┘            │
│         │                         │                             │
│         ▼                         ▼                             │
│  variant_calls          all_unique_sites.vcf.gz                 │
│  table (Iceberg)                  │                             │
│                                   ▼                             │
│                    ┌──────────────────────────────┐             │
│                    │ VEP Workflow (EXISTING)       │             │
│                    │ workflow_definition_5035092   │             │
│                    │ ensemblorg/ensembl-vep:113.4  │             │
│                    └──────────────┬───────────────┘             │
│                                   │                             │
│                                   ▼                             │
│                    variant_annotations table (Iceberg)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    QUERY TIME                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Athena: SELECT ... FROM variant_calls v                        │
│          JOIN variant_annotations a ON (chrom,pos,ref,alt)      │
│                          │                                      │
│                          ▼                                      │
│              AI Agent (Strands + Streamlit)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Effort Estimate

| Task | Complexity | Notes |
|------|-----------|-------|
| Extract Unique Sites workflow (Nextflow) | Medium | New workflow — bcftools per-chromosome scatter |
| bcftools container in ECR | Low | Clone via pull-through cache |
| Raw VCF loader (no VEP) | Low | Modify `load_vcf_schema3.py` to skip annotation fields |
| Annotations table schema | Low | New Iceberg table — chrom, pos, ref, alt + annotation columns |
| VEP annotation loader | Medium | Parse VEP output into annotations table (different schema) |
| Agent query updates | Low | Update Athena queries to use JOIN |
| VCF list generator | Low | `aws s3 ls` + awk script |
| Incremental pipeline | Medium | Lambda + Athena diff + VEP on novel sites |

**Total new code:** ~1 new Nextflow workflow + schema changes + loader modifications. The VEP workflow itself is unchanged.

---

## When to Use Which Approach

| Scenario | Approach |
|----------|----------|
| POC / demo (1-10 samples) | Current per-sample VEP — simple, works |
| Small cohort (10-100 samples) | Per-sample VEP with HealthOmics Batch runs |
| Medium cohort (100-1000 samples) | Annotate-once with unique sites extraction |
| Large cohort (1000+ samples) | Full annotate-once with incremental updates |
| Ongoing ingestion (new samples daily) | Incremental: load raw, diff, annotate novel only |

---

## Containers Required

| Container | Source | Purpose |
|-----------|--------|---------|
| `ensemblorg/ensembl-vep:113.4` | Already in ECR (amd64) | VEP annotation |
| `biocontainers/bcftools:1.17` | Quay.io via pull-through cache | Site extraction + VCF manipulation |

Both are available via the existing quay.io pull-through cache in the account.
