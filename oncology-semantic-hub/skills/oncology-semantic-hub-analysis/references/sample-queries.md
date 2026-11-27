# Sample Queries — Oncology Semantic Hub

These are **verified examples**, not a closed catalog. Each query was ground-truth-validated against `g-8aalvitz38` and `oncology_semantic_hub` as part of the benchmark MVP, so you can trust the result shape and the expected numbers.

**Do not paste these verbatim for arbitrary user questions.** The agent's job is to:

1. Discover the live schema first (`get_graph_schema` for Neptune, `list-table-metadata` for Athena).
2. Read the user's question and identify the entities, filters, and relationships involved.
3. **Generate** the appropriate Cypher or SQL using the schema + the patterns illustrated below.
4. Use these examples as **templates and confidence anchors**: copy the shape (`MATCH (g:gene_protein {name: $X})-[:drug_protein]-(d:drug)`) and adapt the parameters. If the user's question requires a different filter, projection, or traversal, write a different query — don't force-fit.

The examples here cover four query patterns (graph-only, lake-only, cross-system, multi-hop) plus the four Streamlit demo scenarios. They are not exhaustive — many real user questions will need queries that combine elements from multiple examples or introduce new ones.

## Pattern A — Graph-only

### A1. Drugs targeting a specific gene
```cypher
MATCH (g:gene_protein {name: 'TP53'})-[:drug_protein]-(d:drug)
RETURN d.name AS drug
ORDER BY drug
```
**Verified result:** 8 drugs including Zinc chloride, Acetylsalicylic acid, AZD 3355.

### A2. Pathways for a specific gene
```cypher
MATCH (p:pathway)-[:pathway_protein]-(g:gene_protein {name: 'EGFR'})
RETURN p.name AS pathway
ORDER BY pathway
```
**Verified result:** 35 pathways including Signaling by EGFR, EGFR downregulation, ERBB2-related signaling.

### A3. Count of disease nodes (graph metadata)
```cypher
MATCH (d:disease)
RETURN count(d) AS total
```
**Verified result:** 17,080.

### A4. Drug-protein edge count for a gene
```cypher
MATCH (g:gene_protein {name: 'BRCA1'})-[:drug_protein]-(:drug)
RETURN count(*) AS edges
```
**Verified result:** 0. Not a bug — PrimeKG's drug_protein edges are direct binders only; PARP inhibitors target PARP, not BRCA1.

### A5. ClinVar pathogenic count (enrichment property lookup)
```cypher
MATCH (g:gene_protein {name: 'TP53'})
RETURN g.clinvar_pathogenic_count AS count
```
**Verified result:** 1,661.

### A6. COSMIC Tier 1 driver genes
```cypher
MATCH (g:gene_protein {cosmic_tier: 1})
RETURN count(g) AS count
```
**Verified result:** 74.

## Pattern B — Lake-only

### B1. Distinct patients with a specific gene mutation in a cancer type
```sql
SELECT COUNT(DISTINCT case_id) AS patients
FROM oncology_semantic_hub.tcga_mutations
WHERE project_id = 'TCGA-GBM' AND hugo_symbol = 'TP53';
```
**Verified result:** 114.

### B2. Top N mutated genes (by distinct patient count) in a cancer type
```sql
SELECT hugo_symbol, COUNT(DISTINCT case_id) AS patients
FROM oncology_semantic_hub.tcga_mutations
WHERE project_id = 'TCGA-BRCA'
GROUP BY hugo_symbol
ORDER BY patients DESC
LIMIT 5;
```
**Verified result:** TP53 (330), PIK3CA (328), TTN (182), CDH1 (128), GATA3 (125).

### B3. Cancer types with at least one HIGH-impact mutation in a gene
```sql
SELECT COUNT(DISTINCT project_id) AS n_cancer_types
FROM oncology_semantic_hub.tcga_mutations
WHERE hugo_symbol = 'TP53' AND vep_impact = 'HIGH';
```
**Verified result:** 27.

### B4. Mutation rate of a gene in a cancer type (percentage)
```sql
WITH total AS (
  SELECT COUNT(DISTINCT case_id) AS total_count
  FROM oncology_semantic_hub.tcga_mutations
  WHERE project_id = 'TCGA-GBM'
),
gene AS (
  SELECT COUNT(DISTINCT case_id) AS gene_count
  FROM oncology_semantic_hub.tcga_mutations
  WHERE project_id = 'TCGA-GBM' AND hugo_symbol = 'PTEN'
)
SELECT total.total_count, gene.gene_count,
       ROUND(100.0 * CAST(gene.gene_count AS DOUBLE) / total.total_count, 2) AS percentage
FROM total, gene;
```
**Verified result:** 116/371 = 31.27%.

## Pattern C — Cross-system

### C1. Top N mutated genes in cancer type, with their drug counts in the graph

**Step 1 (Athena):**
```sql
SELECT hugo_symbol, COUNT(DISTINCT case_id) AS patients
FROM oncology_semantic_hub.tcga_mutations
WHERE project_id = 'TCGA-BRCA'
GROUP BY hugo_symbol
ORDER BY patients DESC
LIMIT 3;
```
Returns: TP53 (330), PIK3CA (328), TTN (182).

**Step 2 (Neptune, for each gene):**
```cypher
MATCH (g:gene_protein {name: $gene_name})-[:drug_protein]-(d:drug)
RETURN count(d) AS drug_count
```
**Verified result:** TP53 → 8 drugs, PIK3CA → 7 drugs, TTN → 0 drugs.

### C2. Drug Repurposing — top mutated + drugs + ClinVar pathogenic counts

Streamlit demo equivalent: *"Top 5 most mutated genes in TCGA breast cancer, which have approved drugs targeting them, and their ClinVar pathogenic variant counts."*

**Step 1 (Athena):** same as C1 but `LIMIT 5` — returns top 5 BRCA mutated genes.

**Step 2 (Neptune):** for each gene, get drug count AND ClinVar count in a single query:
```cypher
MATCH (g:gene_protein {name: $gene_name})
OPTIONAL MATCH (g)-[:drug_protein]-(d:drug)
RETURN g.name AS gene,
       g.clinvar_pathogenic_count AS clinvar_count,
       count(DISTINCT d) AS drug_count
```

**Verified result (synthesized):**

| Gene | Patients (BRCA) | Drugs | ClinVar pathogenic |
|------|-----------------|-------|--------------------|
| TP53 | 330 | 8 | 1,661 |
| PIK3CA | 328 | 7 | 111 |
| TTN | 182 | 0 | 9,931 |
| CDH1 | 128 | 0 | 1,123 |
| GATA3 | 125 | 0 | 58 |

The `OPTIONAL MATCH` is important — without it, genes with 0 drugs are dropped from the result. The skill should always cite both the patient count (from lake) and the graph-derived enrichment (drugs, ClinVar) to give a complete answer.

### C3. Pan-Cancer Biomarkers — HIGH-impact in many cancer types + disease associations

Streamlit demo equivalent: *"Which genes have HIGH-impact mutations in more than 20 different cancer types? For the top 3, what diseases are they associated with?"*

**Step 1 (Athena):** find genes with HIGH-impact mutations across >20 of the 33 TCGA cancer types:
```sql
SELECT hugo_symbol,
       COUNT(DISTINCT project_id) AS n_cancer_types,
       COUNT(DISTINCT case_id) AS n_patients
FROM oncology_semantic_hub.tcga_mutations
WHERE vep_impact = 'HIGH'
GROUP BY hugo_symbol
HAVING COUNT(DISTINCT project_id) > 20
ORDER BY n_cancer_types DESC, n_patients DESC
LIMIT 5;
```
**Verified result:** TP53 (27 cancers, 829 patients), TTN (27, 546), NF1 (27, 245), ARID1A (25, 407), KMT2C (25, 207).

**Step 2 (Neptune):** for top 3, count disease associations:
```cypher
MATCH (g:gene_protein {name: $gene_name})-[:disease_protein]-(d:disease)
RETURN count(DISTINCT d) AS n_diseases
```
**Verified result:** TP53 → 257 diseases, TTN → 35, NF1 → 112.

Note this query has no partition prune (intentional — pan-cancer aggregation needs all 33 partitions). The query takes ~5 seconds and scans the full mutations table; cite that to the user.

### C4. GBM Pathways — high-frequency mutations + pathway membership

Streamlit demo equivalent: *"For glioblastoma, find genes mutated in more than 10% of patients, then tell me what biological pathways those genes are involved in."*

**Step 1 (Athena):** genes mutated in >10% of TCGA-GBM patients (single-query CTE):
```sql
WITH t AS (
  SELECT COUNT(DISTINCT case_id) AS total
  FROM oncology_semantic_hub.tcga_mutations
  WHERE project_id = 'TCGA-GBM'
)
SELECT m.hugo_symbol,
       COUNT(DISTINCT m.case_id) AS patients,
       ROUND(100.0 * COUNT(DISTINCT m.case_id) / t.total, 1) AS pct
FROM oncology_semantic_hub.tcga_mutations m, t
WHERE m.project_id = 'TCGA-GBM'
GROUP BY m.hugo_symbol, t.total
HAVING COUNT(DISTINCT m.case_id) > 0.10 * t.total
ORDER BY pct DESC;
```
**Verified result (top 6):** PTEN (31.3%), TP53 (30.7%), TTN (22.4%), EGFR (22.1%), MUC16 (12.7%), NF1 (10.5%).

**Step 2 (Neptune):** for each gene, count pathway memberships:
```cypher
MATCH (p:pathway)-[:pathway_protein]-(g:gene_protein {name: $gene_name})
RETURN count(p) AS n_pathways
```
**Verified result:** PTEN → 12 pathways, TP53 → 40, TTN → 2, EGFR → 35, MUC16 → 6.

Use this pattern when the user asks "what pathways are dysregulated in cancer X" — it goes from clinical observation (mutation frequency) to molecular mechanism (pathway disruption).

### C5. Compare Cancers — shared and unique mutated genes between two cohorts

Streamlit demo equivalent: *"Compare the mutation landscape of TCGA-BRCA and TCGA-LUAD. Which genes are uniquely mutated in each, and which are shared?"*

**Step 1 (Athena):** counts of shared vs unique HIGH-impact genes:
```sql
WITH brca AS (
  SELECT DISTINCT hugo_symbol
  FROM oncology_semantic_hub.tcga_mutations
  WHERE project_id = 'TCGA-BRCA' AND vep_impact = 'HIGH'
),
luad AS (
  SELECT DISTINCT hugo_symbol
  FROM oncology_semantic_hub.tcga_mutations
  WHERE project_id = 'TCGA-LUAD' AND vep_impact = 'HIGH'
)
SELECT
  (SELECT COUNT(*) FROM brca) AS brca_total,
  (SELECT COUNT(*) FROM luad) AS luad_total,
  (SELECT COUNT(*) FROM brca b WHERE EXISTS (SELECT 1 FROM luad l WHERE l.hugo_symbol = b.hugo_symbol)) AS shared,
  (SELECT COUNT(*) FROM brca b WHERE NOT EXISTS (SELECT 1 FROM luad l WHERE l.hugo_symbol = b.hugo_symbol)) AS brca_only,
  (SELECT COUNT(*) FROM luad l WHERE NOT EXISTS (SELECT 1 FROM brca b WHERE b.hugo_symbol = l.hugo_symbol)) AS luad_only;
```
**Verified result:** BRCA total 4,764 distinct genes; LUAD total 6,886; shared 2,571; BRCA-only 2,193; LUAD-only 4,315.

**Step 2 (Athena):** top shared HIGH-impact genes by combined patient count:
```sql
SELECT hugo_symbol,
       COUNT(DISTINCT CASE WHEN project_id = 'TCGA-BRCA' THEN case_id END) AS brca_patients,
       COUNT(DISTINCT CASE WHEN project_id = 'TCGA-LUAD' THEN case_id END) AS luad_patients,
       COUNT(DISTINCT case_id) AS total_patients
FROM oncology_semantic_hub.tcga_mutations
WHERE project_id IN ('TCGA-BRCA', 'TCGA-LUAD') AND vep_impact = 'HIGH'
GROUP BY hugo_symbol
HAVING COUNT(DISTINCT CASE WHEN project_id = 'TCGA-BRCA' THEN case_id END) > 0
   AND COUNT(DISTINCT CASE WHEN project_id = 'TCGA-LUAD' THEN case_id END) > 0
ORDER BY total_patients DESC
LIMIT 5;
```
**Verified result:** TP53 (BRCA 85, LUAD 64), GATA3 (87, 2), CDH1 (70, 1), TTN (27, 35), MAP3K1 (59, 1).

This pattern uses Athena's `CASE WHEN ... GROUP BY` to do cohort comparison in a single query — more efficient than two separate queries + Python set ops. Adapt by changing the project_id IN clause for any cohort comparison.

## Pattern D — Multi-hop

### D1. Top diseases sharing genes with breast carcinoma (excluding self and exact synonyms)

```cypher
MATCH (bc:disease {name: 'hereditary breast carcinoma'})-[:disease_protein]-(gp:gene_protein)
WITH COLLECT(DISTINCT gp) AS bc_genes
MATCH (other:disease)-[:disease_protein]-(shared:gene_protein)
WHERE shared IN bc_genes
  AND other.name <> 'hereditary breast carcinoma'
  AND NOT (other.name CONTAINS 'breast')
WITH other, COUNT(DISTINCT shared) AS shared_count
RETURN other.name AS disease, shared_count
ORDER BY shared_count DESC
LIMIT 5
```
**Verified result:** lung cancer (10), type 2 diabetes mellitus (8), diabetes mellitus (8), colorectal cancer (6), pancreatitis (6).

Note: this is a multi-hop traversal where the choice of starting disease (`hereditary breast carcinoma` vs `breast carcinoma` vs `breast cancer`) materially changes the result. State your assumption.

### D2. Drugs targeting PPI neighbors of disease-associated genes

```cypher
MATCH (d:disease {name: 'glioblastoma'})-[:disease_protein]-(g:gene_protein)
MATCH (g)-[:protein_protein]-(neighbor:gene_protein)
MATCH (neighbor)-[:drug_protein]-(drug:drug)
RETURN drug.name AS drug, neighbor.name AS direct_target, g.name AS glioblastoma_gene
LIMIT 10
```
**Verified result:** 10+ drugs found, including Amlexanox → FGF1 → FGFR1 (glioblastoma gene), Alvocidib → CDK1 → ESR1, Thalidomide → NFKB1 → RELA. Multiple valid traversals exist; results depend on which glioblastoma gene the agent reaches first.

## Notes on use

- **Always check `references/caveats.md`** before reporting results — some queries hit known data gaps.
- For Athena, **always include `WHERE project_id = '...'`** when the table is partitioned on that column. Skipping it scans all 33 partitions.
- For Neptune, **edge directionality matters but is not always strict** — `drug_protein` is undirected in PrimeKG, so use `-[:drug_protein]-` (no arrow) to match either direction.
- When in doubt about edge direction or label exact spelling, run `get_graph_schema()` first.
