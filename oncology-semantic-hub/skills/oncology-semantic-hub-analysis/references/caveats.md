# Known Caveats — Oncology Semantic Hub

These are documented gaps between Neptune (PrimeKG) and Athena (TCGA). When a query result hits one of these, mention it explicitly so the user understands.

## Cross-system ontology misalignment (measured)

| Gap | Count | Root cause |
|-----|-------|-----------|
| Genes in Athena `tcga_mutations.hugo_symbol` not in PrimeKG | 227 / 18,885 (1.2%) | Non-coding RNA loci (`AC004076.1`, `AC005324.2`, etc.) reported by VEP but absent from PrimeKG's protein-coding set |
| TCGA project → MONDO mappings that are approximate, not exact | 6 / 33 | TCGA-LGG, TCGA-SKCM, TCGA-PCPG, etc. map to parent or sibling MONDO terms; the exact subtype isn't in PrimeKG |
| PrimeKG genes not in HGNC | ~187 / 27,671 | Deprecated Entrez IDs or non-human genes that HGNC doesn't cover |

**Practical implication:** when an agent runs cross-system queries (Pattern C), 1–2% of mutations may not have graph counterparts. This is normal, not a bug. Mention it if the user asks why a specific gene appears in mutations but has no drug/pathway data.

### How we resolved this at the data curation layer

These gaps came up during the original ingestion pipeline. The curation agents (the same kind of agent reading this caveats file at runtime) handled them as follows:

| Misalignment type | Curation-layer resolution | Where it happened |
|-------------------|--------------------------|-------------------|
| TCGA project (`TCGA-BRCA`) → MONDO disease ID | Manually authored `tcga_to_mondo.csv` mapping table — 33 entries, 27 exact + 6 approximate | `oncology_semantic_hub/scripts/02_build_mappings.py` |
| Hugo gene symbol → Entrez Gene ID (PrimeKG identifier) | Joined against HGNC's complete gene set (`hgnc_complete_set.txt`); achieved 99.3% coverage (27,484 / 27,671 genes) | Same script |
| Disease nodes in PrimeKG with no ICD-10 cross-reference | Enriched 500 disease nodes with `icd10`, `ncit`, `mondo_definition` properties from MONDO OBO | `oncology_semantic_hub/scripts/...` (MONDO enrichment step) |
| ClinVar pathogenic variant counts not in PrimeKG | Computed externally and merged onto 6,286 gene_protein nodes as `clinvar_pathogenic_count` property | `oncology_semantic_hub/scripts/11_add_clinvar.py` |
| COSMIC Tier 1 driver gene flags | Computed externally and merged onto 74 gene_protein nodes as `cosmic_tier` property | `oncology_semantic_hub/scripts/14_add_cosmic.py` |

What's left after curation is the residual gap shown in the table above (~1.2% of mutation genes, 6 approximate disease mappings). That residue is what the agent encounters at runtime.

### Core vs extension placement (architectural note)

The ClinVar and COSMIC enrichments above are stored as **properties on core `gene_protein` nodes**
(`clinvar_pathogenic_count`, `clinvar_top_significance`, `cosmic_tier`). Per the Semantic Data Layer spec, the
**Core Graph data sources are UniProt / Ensembl / HGNC / GO / HPO / OBO only** — ClinVar and COSMIC are *not* core:

- **COSMIC (`cosmic_tier`)** = cancer-driver classification → really an **Oncology** extension attribute.
- **Germline ClinVar (`clinvar_*`)** → a **Rare Disease** extension concern (`urn:rare:variants`); ClinVar IDs
  also ride on Oncology somatic variants.

They were stamped onto core during the original build (`11_add_clinvar.py` / `14_add_cosmic.py`, ~Jul 2026),
*before* the core/extension model was formalized — so they are a **legacy deviation kept for query convenience**,
not a core data source. Note `cosmic_tier` = **CGC Tier-1 driver flags only (74 genes)**, not the full COSMIC
somatic catalog. Contrast the v3 RODA work (CIViC/Genoxus), which correctly kept enrichment in the `ta_oncology`
extension + lake **without touching core**. Two distinct ClinVar layers now exist: **gene-level count** on core
nodes (this note) vs **variant-level positional** ClinVar in `oncology_semantic_hub_roda.genoxus_clinvar` (v3).
Migration of the legacy core properties into the extension is tracked in the product backlog.

### Runtime resolution path: OLS MCP server

When a user's question hits ontology misalignment that the curation layer didn't anticipate (e.g., user uses a non-canonical disease synonym, or provides a clinical code like ICD-10 / SNOMED), the agent should escalate to the **`ontology-lookup-service`** MCP server if it's available in the runtime.

OLS gives the agent live access to 200+ biomedical ontologies (MONDO, HPO, ChEBI, GO, SNOMED, EFO, DOID, and more) via the EBI Ontology Lookup Service. The 7 OLS tools cover:

- **Synonym resolution** (`search_terms`): "stomach cancer" → canonical MONDO label "gastric cancer"
- **Cross-reference lookups** (`get_term_info`): MONDO ID → ICD-10 / SNOMED / NCIt codes for clinical coding integration
- **Hierarchy navigation** (`get_term_ancestors`, `get_term_children`): when a user asks about a parent or subtype not in PrimeKG
- **Similarity search** (`find_similar_terms`): when a user's term is close to but not exact in PrimeKG

This is a deliberate **runtime resolution** path, not a curation update. The curation layer is frozen at v1; new ontology questions that come up in production are handled by the agent calling OLS, not by re-running the ingestion pipeline. See the SKILL.md "Step 6 — Resolve ontology misalignment at runtime" section for the resolution flow.

The OLS MCP server is part of the HCLS toolkit and deployable from `mcp-servers/agentcore-runtime/ontology-lookup-service/` in the source repo.

## Counter-intuitive but correct results

These look like bugs but are real findings. Report them confidently with the explanation:

| Query | Result | Why it's correct |
|-------|--------|------------------|
| `MATCH (g:gene_protein {name:'BRCA1'})-[:drug_protein]-(:drug) RETURN count(*)` | 0 | PrimeKG's `drug_protein` edges are direct binders only. PARP inhibitors (Olaparib, etc.) target PARP1, not BRCA1 directly. The synthetic-lethal relationship between BRCA1-mutant tumors and PARP inhibitors is therapeutically real but not a direct binding edge. |
| TCGA-BRCA top mutated gene | TP53 (330 patients) | Real. Note this is by distinct case count, not mutation count — a single patient can have multiple mutations. |
| TTN appears in many cancer types | Real | TTN is the largest gene in the human genome; its size makes it statistically likely to acquire passenger mutations. Almost always a passenger, not a driver. Worth flagging when reporting. |

## Multi-hop traversal variability

Multi-hop queries (Pattern D) can produce different valid results depending on:

- **Starting disease name.** Querying "breast carcinoma" vs "hereditary breast carcinoma" vs "breast cancer" returns different gene sets — these are separate disease nodes in MONDO/PrimeKG, not synonyms.
- **Edge direction in undirected edges.** Most PrimeKG edges (`drug_protein`, `disease_protein`, `protein_protein`) are undirected. Use `-[:edge_type]-` (no arrow) to match both directions.
- **LIMIT and ordering.** Without a deterministic `ORDER BY`, results from `LIMIT 10` queries can vary between runs.

When reporting multi-hop results, **state the starting node and traversal explicitly** so the user can replicate.

## Data freshness

- **PrimeKG version:** v2 (the version when we ingested in April 2026). Updates are not automatic.
- **TCGA mutations:** GDC snapshot from April 30, 2026. Athena reflects that snapshot.
- **ClinVar enrichment:** April 2026 release. `clinvar_pathogenic_count` reflects ClinVar at that point.
- **COSMIC Cancer Gene Census:** April 2026 release. `cosmic_tier = 1` reflects 74 Tier-1 driver genes per CGC v99.

If a researcher asks about a gene/drug/disease added after April 2026, this hub won't reflect it. Suggest they check the live source.

## Out-of-scope queries

Some questions look like they'd fit this hub but actually need other skills:

| Question | Why this hub can't answer well | Use instead |
|----------|------------------------------|-------------|
| "What does the recent literature say about EGFR resistance?" | No literature data in the hub | `research-deep-literature-review` skill + `pubmed` MCP |
| "What clinical trials are active for KRAS-mutant NSCLC?" | No trial data in the hub | `clinical-trial-search` skill + `clinical-trials` MCP |
| "Map ICD-10 code C50.9 to MONDO" / "What is the SNOMED code for breast cancer?" | Only 500 disease nodes have ICD-10 enrichment | **Use the `ontology-lookup-service` MCP server directly** — `get_term_info` returns cross-references across 200+ ontologies. This is also the right tool when a user's term doesn't match PrimeKG's exact label (see SKILL.md Step 6). |
| "What patients in our internal cohort match TCGA's TP53-mutant pattern?" | Hub is TCGA-only; no internal-cohort data | Out of scope; would require ingesting the cohort first |

If a question hits one of these, redirect to the appropriate skill or MCP server. For ontology questions specifically, OLS is now an in-skill resolution path (see Step 6 in SKILL.md), not a hand-off.
