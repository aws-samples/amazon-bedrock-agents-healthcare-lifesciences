# `scripts/` — Data setup pipeline

Builds the Oncology Semantic Hub: the **S3/Athena data lake** and the **Neptune Analytics
knowledge graph**, plus the ontology enrichments.

> **File numbers are the order the scripts were written, NOT the order they run.** Use the
> orchestrator — [`run_pipeline.py`](run_pipeline.py) — which encodes the correct execution
> order and runs every stage, including the steps that used to be manual.

## Quick start

```bash
# from oncology_semantic_hub/
python scripts/run_pipeline.py --list        # see the ordered plan
python scripts/run_pipeline.py --dry-run     # print exact commands, touch nothing
python scripts/run_pipeline.py               # run the whole pipeline in order
python scripts/run_pipeline.py --from 07 --to 09   # run a contiguous range
python scripts/run_pipeline.py --only 12     # run a single stage
python scripts/run_pipeline.py --verify      # just run end-to-end validation
```

## Execution order (what `run_pipeline.py` runs)

| Step | Script | Group | Purpose |
|---|---|---|---|
| 01 | `01_download_primekg.py` | Extract | Download PrimeKG (KG backbone) from Harvard Dataverse |
| 02 | `02_build_mappings.py` | Extract | ID crosswalks: TCGA project→MONDO, HUGO→Entrez |
| 03 | `03_extract_gdc_clinical.py` | Extract | GDC clinical + biospecimen → `data/gdc/` (→ case/sample nodes) |
| 04 | `04_extract_gdc_molecular.py` | Extract | GDC somatic mutations → S3 `lake/` Parquet |
| 05 | `05_extract_cbioportal.py` | Extract | cBioPortal CNA + expression → S3 `lake/` Parquet |
| 06 | `10_complete_expression.py` | Extract | Backfill expression for remaining TCGA studies → `lake/` |
| 07 | `07_create_athena_tables.py` ⭐ | Athena | Run the Glue crawler over `lake/` → create the Athena tables |
| 08 | `06_primekg_to_neptune.py` | Graph | Build openCypher node/edge CSVs → upload to S3 `neptune/` |
| 09 | `08_neptune_bulk_import.py` ⭐ | Graph | Bulk-import the CSVs into Neptune Analytics |
| 10 | `11_add_clinvar.py` | Enrich | Enrich gene nodes with ClinVar pathogenic counts |
| 11 | `14_add_cosmic.py` | Enrich | Enrich gene nodes with COSMIC CGC Tier-1 flags |
| 12 | `15_add_mondo.py` ⭐ | Enrich | Enrich disease nodes with MONDO icd10/ncit/definition |
| 13 | `12_graph_algorithms.py` | Analytics | Optional: centrality/community/pagerank → `data/analytics/` |
| 14 | `09_validate.py` | Validate | End-to-end validation (Neptune + Athena QA checks) |

⭐ = **newly scripted**. Steps 07 and 09 were previously manual (console crawler run / hand-run
Neptune import); step 12 (MONDO) was previously not checked in. All three now support `--dry-run`.

## Configuration — [`_config.py`](_config.py)

Every script reads its AWS identifiers from `_config.py`, which is environment-overridable so a
rebuild in a **new account/region** needs no code edits:

```bash
export SEMHUB_ACCOUNT_ID=123456789012
export SEMHUB_REGION=us-west-2
export SEMHUB_GRAPH_ID=g-xxxxxxxx          # existing graph, for enrichment/validation
export SEMHUB_ATHENA_DB=oncology_semantic_hub
export SEMHUB_CRAWLER=oncology-hub-crawler
export SEMHUB_GLUE_ROLE_ARN=arn:aws:iam::123456789012:role/<glue-crawler-role>   # step 07 (if crawler absent)
export SEMHUB_IMPORT_ROLE_ARN=arn:aws:iam::123456789012:role/<neptune-import-role>  # step 09
```

Defaults reproduce the reference deployment (`<account-id>` / `us-west-2` / `<your-graph-id>`).

## Prerequisites

- Python venv: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`
- AWS credentials with: S3 (bucket RW), Glue (crawler + catalog), Athena, Neptune Analytics
  (`neptune-graph:*` incl. import), and IAM to create the Glue + Neptune import roles.
- The **Glue role** (step 07) and **Neptune import role** (step 09) — set via the env vars above.
- A first-time build creates a **new** Neptune graph: run step 09 with
  `python scripts/08_neptune_bulk_import.py --new <graphName>`, then export the printed
  `SEMHUB_GRAPH_ID` before running the enrichment/validation stages.

## Known issues (see `docs/data-pipeline-rebuild.md` for detail)

1. **CNA table naming** — the crawler splits `lake/tcga_cna/` into per-project tables
   (`project_id_tcga_*`) + `source_cbioportal` instead of one partitioned `tcga_cna`.
2. **`tcga_mutations` has no `sample_id` column** — join on `case_id`.
3. **Clinical demographics live on Neptune `:case` nodes, not in Athena.**
4. **`15_add_mondo.py` `--id-format`** must match how step 08 stored `disease.original_id`
   (`curie` = `MONDO:0007254`, `number` = `0007254`, `int` = `7254`); dry-run prints an example.
