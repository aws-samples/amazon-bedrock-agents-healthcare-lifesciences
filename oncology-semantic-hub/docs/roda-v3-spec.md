# RODA v3 — Implementation Spec (variant annotation + actionability)

> **Status: BUILT & validated (2026-07-31)** — demo scope EGFR/chr7. Lake tables + the `ta_oncology` graph
> extension are live in AWS; L3 redeployed with the `query_variant_annotation` tool
> (`oncology_semantic_hub_l3_cff54df6-2c7IrBBFyT`). See **§10 As-built** for what shipped + deviations from this
> spec. Reusable code: `scripts/roda/` (+ README). Plan/decisions: `roda-data-expansion-v3-plan.md`.

## 0. Scope
Lean batch (on the EGFR-GBM thread), each via a **reusable parameterized python script** in `scripts/roda/`:
- **Genoxus** → `genoxus_clinvar` table (variant pathogenicity + disease). **INGEST + flatten** (see §3; the
  access-guide "zero-ETL DIRECT_QUERY" was wrong — the Parquet is deeply nested ClinVar).
- **CIViC** → `civic_evidence` table + Neptune actionability edges (drug + evidence level A–E). **INGEST (light)**.
- WS3 GDC expression (Beat AML/CPTAC-3/CCLE) is spec'd in §7 but **deferred** (off-thread, cross-region).

## 1. Verified facts (read-only, 2026-07-30)
**Hub lake DB:** `oncology_semantic_hub` (Glue), region us-west-2.
**`tcga_mutations`** (1,832,018 rows, Parquet, partition `project_id`): `ssm_id, chromosome, start_position,
end_position, reference_allele, tumor_allele, mutation_subtype, hugo_symbol, ensembl_gene_id, aa_change,
consequence_type, vep_impact, case_id, submitter_id`.
- **Build = GRCh38** (GDC-native fields; empirically EGFR at `chr7:55,146,656`). **Chromosome = `chr7`** (chr prefix).
**Genoxus** (`genoxus-annotation`, CC-BY-4.0, `s3://genoxus-annotation-release`, us-west-2): nested ClinVar
Parquet at `Genoxus-Annotation/GRCh={37,38}/chr=N/bp=<1Mb window>/clinvar.parquet`. Top fields:
`Variant_Type, Genomic_Location{Chromosome,Start,Stop}, Reference_Allele, Alternate_Allele, Host_Genes[],
Protein_Changes[], HGVSs[], Classifications[]{Name,Review_Status,Description,Conditions[]}, RCVs[],
Clinical_Assertions[], Trait_Mappings[]`. **Chromosome = `7`** (no prefix). Update: annually.
**CIViC** (`civic`, CC0, `s3://civic-aws-opendata`, us-west-2): `ClinicalEvidenceSummaries/date=01-Oct-2025/…tsv`
(25 cols): `molecular_profile, molecular_profile_id, disease, doid, phenotypes, therapies,
therapy_interaction_type, evidence_type, evidence_direction, evidence_level, significance, evidence_statement,
citation_id, source_type, …, nct_ids, rating, evidence_status, evidence_id, variant_origin, last_review_date,
evidence_civic_url, …`. Monthly dumps; latest `01-Oct-2025`.

## 2. Target data model (additive; new DB — no Core mutation)
**New Glue DB:** `oncology_semantic_hub_roda` (provenance separation). Data under
`s3://oncology-semantic-hub-data-<account-id>-us-west-2/roda/<table>/`.
- **`genoxus_clinvar`** (flat Parquet): `chrom` (no-prefix, e.g. `7`), `pos` (bigint, =Genomic_Location.Start),
  `ref`, `alt`, `variant_type`, `gene_symbol`, `clinical_significance` (from germline `Classifications[]`),
  `review_status`, `conditions` (array<string>), `build` (=38), `source_snapshot`. Partition: `chrom`.
- **`civic_evidence`** (flat Parquet): `gene`, `variant`, `molecular_profile`, `disease`, `doid`, `therapies`
  (array), `evidence_type`, `evidence_direction`, `evidence_level` (A–E), `significance`, `citation_id` (PMID),
  `evidence_civic_url`, `evidence_status`, `source_snapshot`. Partition: none (small).
- **Graph — CIViC *Oncology TA Extension* (IN SCOPE for the demo; Research Technical Specs §2.1 + §3):** add
  **`CancerBiomarker`** nodes (from CIViC evidence) — and where applicable **`SomaticVariant`** — in a
  **`ta_oncology`** partition, with **`predicts_response_to → Drug`** (direction sensitive/resistant,
  evidence_level) edges + biomarker links to Disease. Nodes **reference existing Core `Gene`/`Drug`/`Disease` by
  their canonical IDs (bridge-node / shared-id pattern)** — **PrimeKG core is never mutated**; the whole
  extension is **droppable** (rollback = delete `partition='ta_oncology'` nodes/edges). Property-graph
  realization: new node labels + a `partition='ta_oncology'` property (= the spec's `urn:ta:oncology` named graph).
- **Two-tier (whitepaper raw-in-lake / semantics-in-graph):** the **graph** holds the *relationships* (multi-hop
  traversal + the story); the **`civic_evidence` Athena table** holds the *full evidence records* (statements,
  all columns, PMIDs) for detail/grounding. Agent flow: traverse graph → discover actionable biomarkers/drugs →
  fetch evidence detail from Athena.
- **Genoxus = lake-only** — germline ClinVar *annotation* (positional lookup), **not** a somatic oncology-extension
  entity → stays an Athena table (`genoxus_clinvar`); no graph nodes.
- **Extension governance (Pillar 3, light):** CIViC is expert-curated; extension writes are provenance/snapshot-
  tagged and confined to `ta_oncology` (never core). Human-validation gate optional for a curated source;
  **required** if we later ingest un-curated extractions.
- **Provenance:** every table carries `source_snapshot` (Genoxus release date; CIViC `01-Oct-2025`) + license
  recorded in `data-provenance.md`.

## 3. `scripts/roda/load_genoxus.py` (reusable, parameterized)
**Purpose:** flatten Genoxus nested ClinVar → `genoxus_clinvar`, subset to join-relevant scope.
**Args:** `--build 38` · `--genes EGFR,PTEN,…` OR `--chroms 7,10,…` (subset; default = genes present in
`tcga_mutations`) · `--out-s3 s3://…/roda/genoxus_clinvar/` · `--apply` (default dry-run).
**Steps:** (1) resolve target chr/bp windows (from `--genes` → coordinates, or `--chroms`); (2) read the
matching `GRCh=38/chr=N/bp=*/clinvar.parquet` (no-sign-request); (3) **flatten**: `chrom=Genomic_Location.Chromosome`,
`pos=Genomic_Location.Start`, `ref=Reference_Allele`, `alt=Alternate_Allele`, `gene_symbol=Host_Genes[0].Symbol`,
`clinical_significance` = germline classification significance (extract from `Classifications[]` where
`Name='GermlineClassification'` → `Description`; **exact field to confirm at build** — Review_Status can be
null), `review_status`, `conditions=[Conditions[].Name]`; (4) write partitioned Parquet to `--out-s3`;
(5) register/repair `oncology_semantic_hub_roda.genoxus_clinvar` (create table + `MSCK REPAIR`/partition add).
**Idempotent** (overwrite by chrom partition). **Join note:** consumer normalizes `tcga.chromosome` via
`replace('chr','')` to match `genoxus_clinvar.chrom`.

## 4. `scripts/roda/load_civic.py` (reusable, parameterized)
**Purpose:** load CIViC clinical evidence → `civic_evidence` table + Neptune actionability edges.
**Args:** `--snapshot 01-Oct-2025` (default latest) · `--out-s3 s3://…/roda/civic_evidence/` · `--apply`
(default dry-run). *(No `--graph` in v3 — graph writes ON HOLD; see §2 Oncology TA Extension.)*
**Steps:** (1) fetch `ClinicalEvidenceSummaries/date=<snapshot>/ClinicalEvidenceSummaries.tsv` (no-sign-request);
(2) clean: split `molecular_profile`→`gene`+`variant`, `therapies`→array, keep `evidence_status='accepted'`;
(3) write Parquet → `oncology_semantic_hub_roda.civic_evidence`. **CIViC = curated _somatic_ actionability**
(the somatic counterpart to Genoxus's germline ClinVar). **Idempotent** (snapshot-scoped overwrite). **Tables
only — no graph / Core writes.**

## 5. Agent tool — `query_variant_annotation` (L3-only)
New `@tool` (drafted in `scripts/roda/agent_tools_variant_annotation.py`; **not** added to the deployed agent
until redeploy approved). **L3-only** (kept out of L1 to preserve the L1<L3 contrast).
- **Signature:** `query_variant_annotation(sql_query: str) -> str` — Athena over `oncology_semantic_hub_roda`
  (`genoxus_clinvar`, `civic_evidence`), same execution pattern as `query_patient_data`.
- **`get_hub_schema` additions:** describe both tables + the join rule — **chr-normalization**
  (`replace(tcga.chromosome,'chr','')=chrom`) **+ representation normalization** (SNV exact-match is safe, but
  **indels differ in VCF vs MAF ref/alt representation → left-align/trim or they silently under-match**) **+
  position + allele match**; and the CIViC `gene`/`doid`/`therapy` join. **Germline caveat (P0):** Genoxus is
  ClinVar **germline** significance — surface it as *annotation*, **never** as somatic driver/pathogenicity of
  the patient's tumor; **somatic** significance/actionability comes from **CIViC**.
- **Provenance in answers:** tag `[ClinVar via Genoxus <snapshot>]` / `[CIViC <snapshot>, evidence level X, PMID]`.

## 6. Demo incorporation (LEAN — no new standalone beats)
Enrich existing beats via a **follow-up prompt**, keeping the 6-beat count (avoid demo fatigue):
- **Beat 1 (cohort) + ClinVar _germline_ annotation:** follow-up — "for our EGFR-mutant cohort, what does
  **ClinVar (germline)** report at these variant positions?" → `query_variant_annotation` (Genoxus), **clearly
  labeled germline annotation — NOT a somatic-pathogenicity claim about the patients** (germline ≠ somatic; P0
  fix). L3-only (L1 can't). *Somatic significance/actionability comes from CIViC next.*
- **Beat 2 (druggability) → _somatic_ actionability:** follow-up — "31 drugs target EGFR; which alterations are
  **clinically actionable** (somatic), with **evidence level (A–E)** and sensitivity/resistance?" → CIViC. L0
  asserts ungrounded; L3 cites CIViC evidence + PMID → RELEASE. Closes the "so what?" gap.
- **P0 correctness rule (bake into the tool + answers):** never present germline ClinVar as somatic patient
  pathogenicity; somatic driver/actionability = CIViC (and later COSMIC/OncoKB).
- Add **2 questions** to `evaluation/demo_questions.json` (`beat1b_germline_annotation`, `beat2c_actionability`);
  score Correctness/Faithfulness with the existing harness. Pin snapshots for reproducibility.

## 7. WS3 GDC expression (spec'd, DEFERRED) — `scripts/roda/gdc_expression_pipeline.py`
`--cohort beataml|cptac3|ccle` — per-sample GDC `augmented_star_gene_counts.tsv` → aggregate to a tidy
expression matrix (gene × sample, tpm) → Parquet `oncology_semantic_hub_roda.expression_<cohort>`; map
`case_id` via GDC API. Cross-region (us-east-1→us-west-2) → **needs cost sign-off (Q7)**; off the EGFR-GBM
thread → separate breadth demo + future `query_expression` tool.

## 8. Test & acceptance
- **load_genoxus:** dry-run prints flattened schema + row counts for EGFR/PTEN; `--apply` creates
  `genoxus_clinvar`; Athena join to `tcga_mutations` returns pathogenicity for ≥1 EGFR variant.
- **load_civic:** dry-run prints cleaned rows for EGFR; `--apply` creates `civic_evidence`; an EGFR actionability
  query returns therapies + evidence level + PMID; `--graph` adds edges (count verified).
- **tool:** `query_variant_annotation` answers both demo follow-ups on the redeployed L3; L1 cannot (tool absent).
- **demo metrics:** the 2 new questions score Correctness=1.0 and Faithfulness≥0.75 on L3.
- **provenance:** every answer carries source + snapshot tags; `data-provenance.md` updated.

## 9. Risks / open items
- **Genoxus significance extraction** — exact nested field for germline Pathogenic/Benign to confirm at build
  (Review_Status was null in sample; likely `Classifications[].Description`).
- **chr normalization** — must strip `chr` consistently (build-time + tool schema hint).
- **Neptune additive** — verify edges reference existing `gene_protein`/`drug` nodes without altering them.
- **Execution gating** — Q1/Q3/Q5 confirmed 2026-07-31; ETL + graph extension + L3 redeploy executed (see §10).

## 10. As-built (2026-07-31) — what shipped + deviations from spec
**Shipped (demo scope EGFR/chr7):**
- `oncology_semantic_hub_roda.civic_evidence` (4,598 rows) + `.genoxus_clinvar` (217,333 rows, chr7).
- `ta_oncology` graph extension: 97 `CancerBiomarker` + 165 `PREDICTS_RESPONSE_TO` edges, bridged to core
  `gene_protein`/`drug` by shared IDs; **core never mutated** (verified drop→0, core `gene_protein`=27,671).
- L3 runtime `oncology_semantic_hub_l3_cff54df6-2c7IrBBFyT` with **L3-only `query_variant_annotation`** +
  updated `get_hub_schema` (+ shared `_run_athena` helper); LF granted on both DBs; IAM `Resource:*` covers RODA.
- Reusable scripts: `scripts/roda/{classify_dataset,load_genoxus,load_civic,graph_extension}.py` + README.

**Deviations from the spec above (intentional / discovered):**
1. `genoxus_clinvar` written as a **single unpartitioned Parquet** (spec §2 said partition by `chrom`) — simpler
   for the bounded chr7 demo scope + immediately Athena-queryable; revisit partitioning if loading many chroms.
2. `clinical_significance` currently **mixes ClinVar germline + somatic/oncogenicity** classifications (e.g.
   "Tier I - Strong", "Likely oncogenic" alongside "Uncertain significance"). **Pending refinement:** split by
   classification type for a precise germline≠somatic label (demo already surfaces mostly *somatic* for tumor variants).
3. Graph model refined: `CancerBiomarker` node = **identity only** (`gene`,`variant`); per-evidence attributes
   (`evidence_level`,`direction`,`pmid`,`disease`) live on the **`PREDICTS_RESPONSE_TO` edge** (two-tier: detail
   in `civic_evidence`). `biomarker_id` keyed by `gene:variant` (CIViC evidence_id not carried) → dedup to 97 EGFR biomarkers.
4. Genoxus loaded **chr7 only** (EGFR anchor); extend with `load_genoxus.py --chroms …`.
5. **L3-only demo** (no L0/L1 comparison) per 2026-07-31 decision.

**Validated:** Athena (CIViC level-A EGFR + cross-db germline-annotation join: Tier I-Strong 34 / Uncertain 27 /
Likely oncogenic 5) · live agent (actionability with PMIDs via `query_variant_annotation`; `ta_oncology`
traversal via `query_knowledge_graph`) · rollback (`graph_extension.py --drop`).
