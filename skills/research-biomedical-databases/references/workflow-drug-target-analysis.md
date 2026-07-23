# Workflow: Drug Target Analysis

> **Tool naming:** Tools below are shown by short name (e.g., `query_opentarget`). When invoking via the AgentCore Gateway, prepend the target prefix: `DatabaseLambda___query_opentarget`. See SKILL.md for details.

Use this workflow when a user asks about drug targets, target tractability, pharmacology, existing therapies, or clinical trials for a target-disease pair.

## Trigger Conditions

- User asks "is X a druggable target?"
- User asks about existing drugs for a target or disease
- User wants to assess target validation evidence
- User asks about clinical trials for a specific compound or mechanism

## Step-by-Step Execution

### Step 1: Get target-disease evidence (Open Targets)

```
Tool: query_opentarget
Parameters:
  prompt: "CDK4 associations with breast cancer"
```

Or for more precise queries, use GraphQL directly (note: `prompt` is always required even when using `query`/`variables`):
```
Tool: query_opentarget
Parameters:
  prompt: "CDK4 breast cancer evidence"
  query: "{ target(ensemblId: \"ENSG00000135446\") { id approvedSymbol associatedDiseases { rows { disease { name } score } } } }"
  variables: {}
```

**Extract from results:** Overall association score, evidence types (genetic, somatic, literature, drugs), tractability assessment.

**Note:** Open Targets uses Ensembl gene IDs. If you only have a gene symbol, first resolve it:
```
Tool: query_ensembl
Parameters:
  prompt: "lookup CDK4 human gene"
  endpoint: "lookup/symbol/human/CDK4"
```
Then use the returned Ensembl ID with `query_opentarget`.

### Step 2: Get target biology (UniProt)

```
Tool: query_uniprot
Parameters:
  prompt: "CDK4 protein function and interactions human"
  max_results: 1
```

**Extract from results:** Protein function, catalytic activity, subcellular location, tissue expression, disease associations.

### Step 3: Check protein interaction network (STRING)

```
Tool: query_stringdb
Parameters:
  prompt: "CDK4 protein interaction network human"
```

**Extract from results:** Top interacting proteins (sorted by confidence score), interaction types (experimental, co-expression, text mining).

**Interpretation:**
- Highly connected targets (many interactors) may have more off-target effects
- Targets with few specific interactions may be safer to modulate
- Look for interactors that are themselves druggable (combination opportunities)

### Step 4: Find existing pharmacology (GtoPdb)

```
Tool: query_gtopdb
Parameters:
  prompt: "CDK4 inhibitors and ligands"
```

**Extract from results:** Known ligands, approved drugs, selectivity data, mechanism of action (inhibitor, agonist, antagonist).

**Validation gate:** If GtoPdb returns results, the target is pharmacologically validated. If empty, check OpenFDA as fallback:
```
Tool: query_openfda
Parameters:
  prompt: "CDK4 inhibitor drugs approved"
```

### Step 5: Check clinical trials (ClinicalTrials.gov)

```
Tool: query_clinicaltrials
Parameters:
  prompt: "CDK4 inhibitor phase 3 breast cancer"
  max_results: 10
```

**Extract from results:** Trial phase, status (recruiting, completed, terminated), intervention, primary outcome measures.

### Step 6 (optional): Safety signals

If existing drugs are found, check adverse events:
```
Tool: query_openfda
Parameters:
  prompt: "palbociclib adverse events serious"
  max_results: 20
```

## Output Format

```
## Drug Target Assessment: [Target Name]

### Target Summary
- **Gene:** [symbol] | **UniProt:** [accession] | **Ensembl:** [ID]
- **Function:** [one-line from UniProt]
- **Tractability:** [small molecule / antibody / other]

### Evidence Score
| Evidence Type | Score | Source |
|--------------|-------|--------|
| Genetic association | [0-1] | Open Targets |
| Somatic mutations | [0-1] | Open Targets |
| Known drugs | [0-1] | Open Targets |
| Literature | [0-1] | Open Targets |
| **Overall** | **[0-1]** | Open Targets |

### Existing Pharmacology
| Drug/Compound | Type | Stage | Mechanism |
|--------------|------|-------|-----------|
| [name] | [approved/clinical/tool] | [phase] | [MOA] |

### Interaction Network
Top 5 interactors: [list with confidence scores]
Druggable interactors: [list — combination therapy opportunities]

### Clinical Trial Landscape
| Trial | Phase | Status | Indication |
|-------|-------|--------|------------|
| [NCT ID] | [I/II/III] | [status] | [disease] |

### Assessment
- **Validated target?** [Yes/No — based on approved drugs or Phase III trials]
- **Novel opportunity?** [where gaps exist in current landscape]
- **Risk factors:** [safety signals, interaction complexity]

### References
[numbered citations for each tool query]
```

## Decision Points

- **If target already has approved drugs:** Focus on differentiation — what's the unmet need? Check adverse events and trials for next-gen compounds.
- **If target is novel (no drugs):** Emphasize tractability assessment, genetic evidence strength, and proximity to validated targets in the network.
- **If user asks about a disease (not a target):** Start with `query_opentarget` using disease name → get top-ranked targets → then run this workflow for each.
- **Alternative: Dedicated Open Targets MCP server** — For complex GraphQL queries involving multiple targets, use `mcp__open-targets__query_open_targets_graphql` instead of the gateway's `query_opentarget`. It offers schema introspection and batch queries.
