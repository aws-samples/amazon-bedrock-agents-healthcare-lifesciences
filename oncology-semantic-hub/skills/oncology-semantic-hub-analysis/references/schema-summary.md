# Schema Summary — Oncology Semantic Hub

This is a static overview. The authoritative schema comes from the MCP servers at runtime via `get_graph_schema` (Neptune) and `manage_aws_athena_databases_and_tables` (Athena).

## Neptune Analytics graph (`g-8aalvitz38`, us-west-2)

**Total: 174,742 nodes, 4,095,616 edges across 12 node types and 30+ edge types.**

### Node types

| Label | Count | Notes |
|-------|-------|-------|
| `gene_protein` | 27,671 | PrimeKG genes/proteins. Properties include `name`, `clinvar_pathogenic_count` (6,286 enriched), `cosmic_tier` (74 Tier-1 driver genes flagged) |
| `disease` | 17,080 | PrimeKG diseases (MONDO IDs). 500 enriched with `icd10`, `ncit`, `mondo_definition` |
| `drug` | 7,957 | DrugBank-derived |
| `pathway` | 2,516 | Reactome |
| `biological_process` | 28,642 | Gene Ontology biological processes |
| `anatomy` | 14,035 | UBERON |
| `effect_phenotype` | 15,311 | HPO |
| `molecular_function` | 11,169 | GO molecular functions |
| `cellular_component` | 4,176 | GO cellular components |
| `exposure` | 818 | Comparative Toxicogenomics Database |
| `case` | 11,428 | TCGA patient cases (added by our enrichment) |
| `sample` | 33,939 | TCGA tissue samples (added by our enrichment) |

### Key edge types

| Edge | What it connects | Direction |
|------|------------------|-----------|
| `drug_protein` | `drug` ↔ `gene_protein` | undirected; query both directions |
| `disease_protein` | `disease` ↔ `gene_protein` | undirected |
| `protein_protein` | `gene_protein` ↔ `gene_protein` | undirected, 321K edges (PPI network) |
| `pathway_protein` | `pathway` ↔ `gene_protein` | undirected |
| `bioprocess_protein` | `biological_process` ↔ `gene_protein` | undirected |
| `case_has_diagnosis` | `case` → `disease` | TCGA case to MONDO disease |
| `sample_from_case` | `sample` → `case` | tissue sample to patient |
| `indication`, `contraindication`, `off-label` | `drug` ↔ `disease` | drug-disease relations |
| `disease_phenotype_positive`/`disease_phenotype_negative` | `disease` ↔ `effect_phenotype` | HPO phenotype links |

Run `get_graph_schema()` for the complete enumeration including additional edge types not shown here.

## Athena database (`oncology_semantic_hub`, us-west-2, workgroup `primary`)

### Tables

| Table | Records | Partitioned on | Purpose |
|-------|---------|---------------|---------|
| `tcga_mutations` | ~1.83M | `project_id` (33 partitions) | Somatic mutations across all 33 TCGA cancer types |
| `tcga_expression` | ~44K | `source`, `project_id` | Gene expression z-scores for 10 driver genes × 32 TCGA studies |
| `source_cbioportal` | ~1.7M | `project_id` | Copy number alterations from cBioPortal |
| `project_id_tcga_acc` | ~705K | none | Per-project CNA (TCGA-ACC) |
| `project_id_tcga_blca` | ~3.15M | none | Per-project CNA (TCGA-BLCA) |

### `tcga_mutations` columns (the most-queried table)

| Column | Type | Notes |
|--------|------|-------|
| `ssm_id` | string | Simple somatic mutation ID |
| `chromosome`, `start_position`, `end_position` | string, bigint, bigint | Genomic coordinates |
| `reference_allele`, `tumor_allele` | string | Variant alleles |
| `mutation_subtype` | string | e.g., `Single base substitution` |
| `hugo_symbol` | string | Gene symbol — **join key to Neptune `gene_protein.name`** |
| `ensembl_gene_id` | string | Ensembl ID (alternate gene identifier) |
| `aa_change` | string | Amino acid change (HGVS-like) |
| `consequence_type` | string | e.g., `missense_variant`, `frameshift_variant`, `stop_gained` |
| `vep_impact` | string | `HIGH`, `MODERATE`, `LOW`, `MODIFIER` |
| `case_id` | string | TCGA case UUID — **join key to Neptune `case.case_id`** |
| `submitter_id` | string | Human-readable case identifier (e.g., `TCGA-BH-A0E0`) |
| `project_id` | string | Partition key — `TCGA-XXX` |

### Cross-system join keys

- **Genes:** Athena `hugo_symbol` ↔ Neptune `gene_protein.name`. ~99% match coverage; 227 unmatched (mostly non-coding RNA loci like `AC004076.1`). See `caveats.md`.
- **Cases:** Athena `case_id` ↔ Neptune `case.case_id`. Athena has ~10K cases with mutations; Neptune has 11,428 cases (those without mutations are still graph-traversable to disease).
- **Cancer types:** Athena `project_id` (e.g., `TCGA-BRCA`) ↔ MONDO disease via the `tcga_to_mondo` mapping. 27 of 33 are exact matches; 6 are approximate. See `caveats.md`.

### TCGA project codes (for partition pruning)

```
TCGA-ACC, TCGA-BLCA, TCGA-BRCA, TCGA-CESC, TCGA-CHOL, TCGA-COAD, TCGA-DLBC,
TCGA-ESCA, TCGA-GBM, TCGA-HNSC, TCGA-KICH, TCGA-KIRC, TCGA-KIRP, TCGA-LAML,
TCGA-LGG, TCGA-LIHC, TCGA-LUAD, TCGA-LUSC, TCGA-MESO, TCGA-OV, TCGA-PAAD,
TCGA-PCPG, TCGA-PRAD, TCGA-READ, TCGA-SARC, TCGA-SKCM, TCGA-STAD, TCGA-TGCT,
TCGA-THCA, TCGA-THYM, TCGA-UCEC, TCGA-UCS, TCGA-UVM
```
