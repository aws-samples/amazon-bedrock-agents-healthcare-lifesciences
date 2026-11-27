# Data Pipeline Rebuild Runbook

**Purpose:** Reproduce the Oncology Semantic Hub — the S3/Athena data lake and the
Neptune Analytics knowledge graph — from scratch.
**Last verified:** 2026-07-08 against live account `<account-id>` / region `us-west-2`.

> This is the single source of truth for rebuilding. It supersedes scattered "how we
> loaded it" notes in `sprint-1-tasks.md` / `sprint-2-tasks.md` (kept for history).

---

## 1. What gets built

| Target | Identifier (current) | Contents |
|---|---|---|
| S3 data lake | `s3://oncology-semantic-hub-data-<acct>-<region>/lake/` | Parquet, partitioned by `project_id` |
| Glue database | `oncology_semantic_hub` | crawled by `oncology-hub-crawler` |
| Athena tables | `tcga_mutations` (1.83M), `tcga_expression` (44K), `source_cbioportal` + `project_id_tcga_*` (CNA, ~1.7M) | see note on CNA naming below |
| Neptune Analytics | graph `<your-graph-id>` (32 m-NCU) | PrimeKG + TCGA case/sample nodes + enrichments |

**Data sources:** PrimeKG (Harvard Dataverse), TCGA via GDC Analysis API, cBioPortal API,
ClinVar, COSMIC CGC, MONDO OBO. Full citations: `docs/data-provenance.md`.

---

## 2. Prerequisites

- Python venv: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`
- AWS creds for `<acct>` with: S3 (bucket RW), Glue (crawler + catalog), Athena, Neptune
  Analytics (`neptune-graph:*` incl. bulk import), IAM (create the Neptune load + Glue roles),
  `bedrock:InvokeModel` (agent only).
- An S3 bucket and an empty Neptune Analytics graph (or let step 6 create/import).
- Set env if identifiers differ from defaults: `SEMHUB_GRAPH_ID`, `SEMHUB_ATHENA_DB`,
  `SEMHUB_ATHENA_OUTPUT` (see `evaluation/config.py`).

---

## 3. Rebuild order (scripts are the executable spec — run from `scripts/`)

| Step | Script | Does | Reads → Writes |
|---|---|---|---|
| 1 | `01_download_primekg.py` | Download PrimeKG, explore schema | Harvard Dataverse → `data/primekg/` |
| 2 | `02_build_mappings.py` | TCGA→MONDO + Hugo→Entrez maps | GDC/refs → `data/mappings/` |
| 3 | `03_extract_gdc_clinical.py` | Clinical + biospecimen for all TCGA cases | GDC API → `data/gdc/tcga_cases.csv`, `tcga_samples.csv` (become **graph case/sample nodes**) |
| 4 | `04_extract_gdc_molecular.py` | Somatic mutations (+CNV/expr) | GDC Analysis API → **S3 `lake/tcga_mutations/` Parquet** |
| 5 | `05_extract_cbioportal.py` | CNA + expression | cBioPortal API → **S3 `lake/tcga_cna/`, `lake/tcga_expression/`** |
| 6 | `10_complete_expression.py` | Backfill remaining expression studies | cBioPortal → `lake/tcga_expression/` |
| 7 | `07_create_athena_tables.py` | **Run the Glue crawler over `lake/`** → create Athena tables | S3 `lake/` → Glue/Athena tables |
| 8 | `06_primekg_to_neptune.py` | Build Neptune openCypher node/edge CSVs and upload | `data/primekg` + `data/gdc` → `data/neptune/*.csv` → S3 |
| 9 | `08_neptune_bulk_import.py` | **Bulk-import the CSVs into Neptune Analytics** | S3 `neptune/` → Neptune graph |
| 10 | `11_add_clinvar.py` | Enrich gene nodes with ClinVar counts | ClinVar → Neptune property writes |
| 11 | `14_add_cosmic.py` | Enrich gene nodes with COSMIC Tier-1 | COSMIC CGC → Neptune property writes |
| 12 | `15_add_mondo.py` | `icd10`/`ncit`/`mondo_definition` on disease nodes | MONDO OBO → Neptune property writes |
| 13 | `12_graph_algorithms.py` | Optional: centrality/community analytics | Neptune → `data/analytics/*.csv` |
| 14 | `09_validate.py` | End-to-end validation (QA checks) | Neptune + Athena |

**Run the whole thing in order** with the orchestrator (encodes this order; file numbers ≠ run
order): `python scripts/run_pipeline.py` (`--list`, `--dry-run`, `--from/--to`, `--only`,
`--verify`). See [`scripts/README.md`](../scripts/README.md). Steps 7, 9 and 12 (Glue crawler,
Neptune import, MONDO enrichment) are **now scripted** — no manual console steps.

---

## 4. Known issues to fix on rebuild (do not reproduce as-is)

1. **CNA table naming is a crawler artifact.** The crawler split `lake/tcga_cna/` into
   per-project tables (`project_id_tcga_acc`, `project_id_tcga_blca`, …) plus
   `source_cbioportal`, instead of one partitioned `tcga_cna` table. Cosmetic fix (optional): land CNA
   under a single prefix partitioned by `project_id` and re-crawl, mirroring `tcga_mutations`.
   **Duplicate-partition-column defect — RESOLVED.** The crawler also listed partition columns
   (`project_id`, `source`) as *both* data columns and partition keys, so Athena rejected
   `source_cbioportal` and `tcga_expression` with *"Table descriptor contains duplicate columns"* (they
   were unqueryable). `07_create_athena_tables.py` now runs `fix_duplicate_partition_columns()` after the
   crawl to strip the duplicates (requires Lake Formation ALTER). cBioPortal CNA (`source_cbioportal`,
   `value` = GISTIC code, 2 = amplification; cohort ids like `gbm_tcga`) and expression are now queryable.
2. **Script numbering gaps (07, 08) — RESOLVED.** These slots are now filled:
   `07_create_athena_tables.py` (Glue crawler) and `08_neptune_bulk_import.py` (Neptune import).
   File numbers still ≠ execution order — use `scripts/run_pipeline.py` (which encodes the order).
3. **MONDO enrichment script — RESOLVED.** Re-authored as `15_add_mondo.py` (downloads the MONDO
   OBO, parses ICD10/NCIT/definition xrefs, batched property writes). Set `--id-format` to match
   how step 08 stored `disease.original_id`.
4. **`tcga_mutations` has no `sample_id` column** (real cols: `ssm_id, chromosome,
   start_position, end_position, reference_allele, tumor_allele, mutation_subtype, hugo_symbol,
   ensembl_gene_id, aa_change, consequence_type, vep_impact, case_id, submitter_id`, partition
   `project_id`). Any tool/prompt referencing `sample_id` on mutations is wrong.

---

## 5. Where clinical data lives (verified 2026-07-08)

Clinical demographics are **graph `case`-node properties**, NOT an Athena table:
`gender, race, ethnicity, age_at_diagnosis (10,573), vital_status (11,301),
primary_diagnosis (11,301), days_to_death (3,615)`. **`tumor_stage` was extracted to
`data/gdc/tcga_cases.csv` but never loaded (0 in graph).**

---

## 6. Verify a rebuild
```
# Athena
SELECT count(*) FROM tcga_mutations;                 -- expect ~1,832,018
# Neptune
MATCH (d:disease) RETURN count(d);                   -- expect 17,080
MATCH (g:gene_protein) RETURN count(g);              -- expect 27,671
MATCH (c:case) RETURN count(c);                      -- expect 11,428
# then:
python scripts/09_validate.py
```
