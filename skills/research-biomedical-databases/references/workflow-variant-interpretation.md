# Workflow: Variant Interpretation

> **Tool naming:** Tools below are shown by short name (e.g., `query_clinvar`). When invoking via the AgentCore Gateway, prepend the target prefix: `DatabaseLambda___query_clinvar`. See SKILL.md for details.

Use this workflow when a user asks about variant pathogenicity, clinical significance, population frequencies, or functional impact of genetic variants.

## Trigger Conditions

- User mentions a specific variant (rs ID, HGVS notation, gene + mutation)
- User asks "is this variant pathogenic?"
- User asks about variant frequency in populations
- User wants a clinical variant report

## Step-by-Step Execution

### Step 1: Identify the variant (ClinVar)

```
Tool: query_clinvar
Parameters:
  prompt: "Find pathogenic variants in BRCA1" (or specific variant)
  search_term: "BRCA1[gene] AND pathogenic[clinical significance]" (optional, more precise)
  max_results: 10
```

**Extract from results:** variant name, RS ID, clinical significance, review status, gene name.

**Validation gate:** If ClinVar returns no results, try:
- Alternative gene names (official HGNC symbol vs. aliases)
- RS number directly if available
- HGVS notation (e.g., "NM_007294.4:c.5266dupC")

### Step 2: Check population frequency (gnomAD)

```
Tool: query_gnomad
Parameters:
  prompt: "BRCA1 variant frequencies"
  gene_symbol: "BRCA1"  ← use this for faster results
```

**Extract from results:** allele frequency (AF), homozygote count, population-specific frequencies.

**Interpretation rules:**
- AF > 1% → likely benign (too common for rare disease)
- AF < 0.01% → consistent with pathogenic for rare disease
- Absent from gnomAD → ultra-rare, supports pathogenic if other evidence exists

### Step 3: Get protein context (UniProt)

```
Tool: query_uniprot
Parameters:
  prompt: "BRCA1 protein domains and functional sites human"
  max_results: 1
```

**Extract from results:** UniProt accession ID (e.g., P38398), functional domains, active sites, post-translational modifications.

**Data passed forward:** UniProt accession ID → used in Step 4.

### Step 4: Check protein structure (AlphaFold)

```
Tool: query_alphafold
Parameters:
  uniprot_id: "P38398"  ← from Step 3 (REQUIRED — this tool does NOT accept prompt)
  endpoint: "prediction"
```

**Extract from results:** pLDDT confidence scores, structural features near variant position.

**Interpretation:** Variants in high-confidence (pLDDT > 70) structured regions are more likely functionally disruptive than those in disordered loops.

### Step 5: Pathway context (Reactome)

```
Tool: query_reactome
Parameters:
  prompt: "BRCA1 DNA repair pathways"
```

**Extract from results:** Pathway names, Reactome stable IDs (R-HSA-xxxxx), pathway hierarchy.

**Purpose:** Establishes biological context — a variant disrupting a critical pathway node has stronger pathogenicity evidence.

### Step 6 (optional): Regulatory impact

Only if the variant is non-coding or intronic:

```
Tool: query_regulomedb
Parameters:
  prompt: "regulatory impact of rs80357906"
```

**Extract from results:** RegulomeDB score (1a-7), chromatin state, TF binding disruption.

## Output Format

Synthesize findings into a structured variant report:

```
## Variant Interpretation Report

**Variant:** [gene] [HGVS] (rs ID)
**Clinical Significance:** [ClinVar classification] (review status: [stars])

### Evidence Summary
| Source | Finding | Interpretation |
|--------|---------|----------------|
| ClinVar | [classification] | [review status] |
| gnomAD | AF = [frequency] | [benign/pathogenic support] |
| UniProt | Domain: [name] | [functional context] |
| AlphaFold | pLDDT: [score] | [structural impact] |
| Reactome | Pathway: [name] | [biological relevance] |

### Clinical Implications
[Summary of actionable findings]

### References
1. ClinVar (Tool: query_clinvar). Query: [description]. Retrieved: [date]
2. gnomAD (Tool: query_gnomad). Query: [description]. Retrieved: [date]
...
```

## Decision Points

- **If variant is well-characterized in ClinVar (3+ stars):** Steps 1-2 may be sufficient. Steps 3-5 add context but may not change classification.
- **If variant is VUS (variant of uncertain significance):** All steps are critical — protein structure and pathway context can help reclassify.
- **If variant is non-coding:** Skip Steps 3-4, add Step 6 (RegulomeDB).
- **If user wants pharmacogenomics:** Add `query_openfda` for drug-gene interactions.
