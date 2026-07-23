# Workflow: Protein Analysis

> **Tool naming:** Tools below are shown by short name (e.g., `query_uniprot`). When invoking via the AgentCore Gateway, prepend the target prefix: `DatabaseLambda___query_uniprot`. See SKILL.md for details.

Use this workflow when a user asks about protein function, structure, domains, interactions, or proteomics data.

## Trigger Conditions

- User asks about protein function or biology
- User asks about protein structure or 3D conformation
- User asks about protein-protein interactions
- User asks about protein domains or families
- User mentions a UniProt ID or protein name

## Step-by-Step Execution

### Step 1: Get protein function and annotation (UniProt)

```
Tool: query_uniprot
Parameters:
  prompt: "Human insulin receptor protein function and domains"
  max_results: 1
```

Or query by accession directly:
```
Tool: query_uniprot
Parameters:
  prompt: "P06213 insulin receptor"
  endpoint: "https://rest.uniprot.org/uniprotkb/P06213"
```

**Extract from results:** UniProt accession ID, protein name, function description, GO annotations, subcellular location, tissue specificity, disease associations.

**Data passed forward:** UniProt accession → Steps 2, 3.

### Step 2: Get protein structure (AlphaFold or PDB)

**For predicted structure (always available):**
```
Tool: query_alphafold
Parameters:
  uniprot_id: "P06213"  ← from Step 1 (REQUIRED)
  endpoint: "prediction"
```

**For experimental structure (if available):**
```
Tool: query_pdb
Parameters:
  prompt: "insulin receptor crystal structure human"
  max_results: 5
```

Then get details for specific PDB IDs:
```
Tool: query_pdb_identifiers
Parameters:
  identifiers: ["4ZXB", "5KQV"]  ← from query_pdb results
  return_type: "entry"
```

**Decision:** Use AlphaFold for full-length predicted structure. Use PDB for experimentally determined structures (higher confidence for specific conformations, but may only cover domains).

### Step 3: Check protein domains (InterPro)

```
Tool: query_interpro
Parameters:
  prompt: "P06213 insulin receptor domains and families"
```

Or use the direct endpoint:
```
Tool: query_interpro
Parameters:
  prompt: "insulin receptor domains"
  endpoint: "/protein/uniprot/P06213"
```

**Extract from results:** Domain annotations (Pfam, SMART, CDD), family membership, functional sites, domain boundaries.

### Step 4: Protein interaction network (STRING)

```
Tool: query_stringdb
Parameters:
  prompt: "insulin receptor INSR protein interactions human"
```

**Extract from results:** Interaction partners with confidence scores (0-1), evidence channels (experimental, co-expression, text mining, database).

**Interpretation:**
- Score > 0.9 = highest confidence (experimentally validated)
- Score 0.7-0.9 = high confidence
- Score 0.4-0.7 = medium confidence (use cautiously)

### Step 5 (optional): Proteomics data (PRIDE)

If the user wants mass spectrometry or proteomics datasets:
```
Tool: query_pride
Parameters:
  prompt: "insulin receptor phosphorylation proteomics"
  max_results: 10
```

**Extract from results:** PRIDE project IDs, experimental type, organism, instrument, publication.

### Step 6 (optional): Electron microscopy structure (EMDB)

For large macromolecular complexes:
```
Tool: query_emdb
Parameters:
  prompt: "insulin receptor ectodomain cryo-EM structure"
```

## Output Format

```
## Protein Analysis Report: [Protein Name]

### Identity
- **Name:** [full name]
- **Gene:** [gene symbol] | **UniProt:** [accession] | **Length:** [aa]
- **Function:** [primary function from UniProt]
- **Subcellular location:** [membrane/cytoplasm/nuclear/etc.]

### Domain Architecture
| Domain | Position | Family | Function |
|--------|----------|--------|----------|
| [name] | [start-end] | [Pfam/SMART] | [brief] |

### Structure
- **AlphaFold:** [confidence summary — % high confidence regions]
- **Experimental (PDB):** [X structures available]
  - [PDB ID]: [resolution], [method], [coverage]

### Interaction Network (top 10)
| Partner | Score | Evidence | Biological role |
|---------|-------|----------|----------------|
| [protein] | [0-1] | [type] | [brief] |

### Disease Associations
| Disease | Evidence | Mechanism |
|---------|----------|-----------|
| [name] | [from UniProt] | [gain/loss of function] |

### References
[numbered citations]
```

## Decision Points

- **If user only needs function:** Step 1 alone is sufficient. UniProt provides comprehensive functional annotation.
- **If user needs structure for drug design:** Steps 1 → 2 (both AlphaFold AND PDB). Experimental structures are preferred for active site modeling.
- **If user asks about a protein complex:** Steps 1 → 4 → 6. STRING shows complex members; EMDB may have the complex structure.
- **If user asks about post-translational modifications:** Steps 1 → 5. UniProt has curated PTM sites; PRIDE has experimental MS data.
- **If user provides only a gene name (not protein):** Start with `query_uniprot` using the gene name with "human" — UniProt resolves gene names to protein entries.
