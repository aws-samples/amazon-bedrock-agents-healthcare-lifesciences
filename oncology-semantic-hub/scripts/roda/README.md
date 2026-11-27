# `scripts/roda/` — RODA → Semantic Hub onboarding toolkit (reusable)

Reusable, parameterized, **idempotent** scripts to onboard AWS Registry of Open Data (RODA) datasets into the
Oncology Semantic Hub. All are **`--dry-run` by default** (read-only) and **`--apply`-gated**; everything is
**additive** (new `oncology_semantic_hub_roda` Glue DB + `ta_oncology` graph partition) and **rollback-able**.
Design: `../../docs/roda-v3-spec.md`; scale plan: `../../docs/roda-master-plan-scale.md`.

| Script | Purpose | Key args |
|---|---|---|
| `classify_dataset.py` | Metadata + S3 preview → onboarding **lane** (build-ETL vs runtime-direct) + rationale | `--slug --bucket --region` |
| `load_genoxus.py` | Flatten nested Genoxus **ClinVar** Parquet → `genoxus_clinvar` lake table (variant annotation) | `--chroms 7,10 [--apply]` |
| `load_civic.py` | CIViC clinical evidence → `civic_evidence` lake table (**somatic actionability**, evidence A–E + PMIDs) | `--snapshot 01-Oct-2025 [--apply]` |
| `graph_extension.py` | CIViC → **Oncology TA graph extension** (`CancerBiomarker`→`predicts_response_to`→`drug`) bridged to core by shared IDs | `--gene EGFR [--apply] [--drop]` |

## Onboarding flow (per dataset)
`classify_dataset.py` (decide lane) → `load_*.py --apply` (lake table) → (if relationships) `graph_extension.py --apply`
(TA extension) → the L3 agent's `query_variant_annotation` tool + `query_knowledge_graph` traverse them.

## Guarantees
- **Core never mutated** — the graph extension only `MATCH`es core `gene_protein`/`drug` and adds new
  `CancerBiomarker` nodes/edges tagged `partition='ta_oncology'`.
- **Rollback** — `graph_extension.py --drop --apply` deletes the extension; drop the `oncology_semantic_hub_roda`
  Glue DB + `s3://…/roda/` prefix to remove the lake tables. (Verified: drop → 0 nodes, core unchanged 27,671.)
- **Provenance** — every table/node carries `source_snapshot` (Genoxus release; CIViC `01-Oct-2025`) + license.

## Current state (chr7 / EGFR demo scope)
- `oncology_semantic_hub_roda.civic_evidence` (4,598 rows) · `.genoxus_clinvar` (217,333 rows, chr7).
- `ta_oncology`: 97 `CancerBiomarker` nodes + 165 `PREDICTS_RESPONSE_TO` edges (EGFR).
- Extend: `load_genoxus.py --chroms <more> --apply`, `graph_extension.py --gene ALL --apply`.

## Known refinement (tracked)
`load_genoxus.py` currently merges ClinVar's germline + somatic/oncogenicity classifications into one
`clinical_significance` column. Planned: split by **classification type** (germline vs somatic) for a precise
germline≠somatic distinction (the demo already surfaces mostly somatic "Tier I - Strong" for tumor variants).
