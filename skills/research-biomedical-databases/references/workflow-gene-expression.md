# Workflow: Gene Expression & Phenotype Analysis

> **Tool naming:** Tools below are shown by short name (e.g., `query_geo`). When invoking via the AgentCore Gateway, prepend the target prefix: `DatabaseLambda___query_geo`. See SKILL.md for details.

Use this workflow when a user asks about gene expression patterns, disease phenotypes, cancer mutations, or regulatory elements for a gene.

## Trigger Conditions

- User asks about gene expression in a tissue or disease
- User asks about phenotypes associated with a gene
- User asks about cancer mutations or tumor profiling
- User wants to find expression datasets for analysis

## Step-by-Step Execution

### Step 1: Find expression data (GEO)

```
Tool: query_geo
Parameters:
  prompt: "TP53 expression in hepatocellular carcinoma RNA-seq"
  max_results: 10
```

**Extract from results:** GEO series IDs (GSE numbers), platforms, sample counts, experimental design.

**Tips for effective GEO queries:**
- Specify data type: "RNA-seq", "microarray", "single-cell"
- Include disease/tissue context
- Add organism if not obvious: "human", "mouse"

### Step 2: Check phenotype associations (Monarch)

```
Tool: query_monarch
Parameters:
  prompt: "TP53 loss of function phenotypes human"
  max_results: 10
```

**Extract from results:** Associated phenotypes (HPO terms), disease associations, model organism phenotypes.

**Note:** Monarch integrates data across species. Specify "human" to focus on clinical phenotypes, or omit for cross-species comparisons useful in drug discovery.

### Step 3: Cancer mutation landscape (cBioPortal)

```
Tool: query_cbioportal
Parameters:
  prompt: "TP53 mutations in liver cancer frequency and type"
```

Or use a direct endpoint for specific studies:
```
Tool: query_cbioportal
Parameters:
  prompt: "TP53 mutations in TCGA liver cancer"
  endpoint: "/studies/lihc_tcga/mutations?hugoGeneSymbol=TP53"
```

**Extract from results:** Mutation frequency, mutation types (missense, nonsense, frameshift), hotspot positions, co-occurring mutations.

### Step 4: Regulatory elements (RegulomeDB)

Only if investigating non-coding regulation or eQTLs:

```
Tool: query_regulomedb
Parameters:
  prompt: "regulatory variants near TP53 promoter region"
```

**Extract from results:** RegulomeDB scores, overlapping TF binding sites, chromatin accessibility, eQTL associations.

### Step 5: Gene model and genomic context (Ensembl)

```
Tool: query_ensembl
Parameters:
  prompt: "TP53 gene structure transcripts human"
  endpoint: "lookup/symbol/human/TP53?expand=1"
```

**Extract from results:** Ensembl gene ID, transcript variants, exon structure, genomic coordinates.

**Data passed forward:** Ensembl ID can be used with `query_opentarget` for disease associations.

### Step 6 (optional): GWAS associations

If investigating common disease risk:

```
Tool: query_gwas_catalog
Parameters:
  prompt: "GWAS associations near TP53 locus cancer risk"
```

**Extract from results:** Associated traits, p-values, effect sizes, lead SNPs.

## Output Format

```
## Gene Expression & Phenotype Report: [Gene]

### Gene Overview
- **Symbol:** [HGNC] | **Ensembl:** [ENSG ID] | **Location:** [chr:start-end]
- **Function:** [brief from UniProt/Ensembl]

### Expression Datasets Available
| GEO ID | Platform | Disease/Tissue | Samples | Type |
|--------|----------|----------------|---------|------|
| [GSE] | [platform] | [context] | [n] | [RNA-seq/array] |

### Cancer Mutation Profile
- **Overall frequency:** [X%] in [cancer type]
- **Hotspot mutations:** [positions and amino acid changes]
- **Mutation types:** [% missense, % nonsense, % frameshift]
- **Co-occurring mutations:** [top co-mutated genes]

### Phenotype Associations
| Phenotype | Source | Evidence |
|-----------|--------|----------|
| [HPO term] | [organism] | [type] |

### Regulatory Context
- **RegulomeDB score:** [if applicable]
- **TF binding:** [overlapping factors]
- **eQTLs:** [associated variants affecting expression]

### References
[numbered citations]
```

## Decision Points

- **If user wants raw data for analysis:** Provide GEO IDs and suggest download. The tool returns metadata, not raw expression matrices.
- **If user asks "is this gene expressed in tissue X?":** Start with GEO, but note that GEO searches find *datasets* about the gene, not direct expression values. For direct expression lookups, suggest GTEx (not available via this gateway).
- **If user wants mutation-expression correlation:** Chain Steps 1 + 3 — find datasets where the gene is mutated AND expression data exists for the same cohort.
- **If comparing across cancer types:** Run `query_cbioportal` multiple times with different cancer endpoints, or use a broad prompt like "TP53 mutations across all TCGA studies."
