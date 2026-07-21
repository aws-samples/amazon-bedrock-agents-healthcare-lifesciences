---
name: research-biomedical-databases
description: Use when querying biomedical databases (UniProt, ClinVar, gnomAD, PDB, Reactome, Open Targets, etc.) via the Biomni AgentCore Gateway MCP server. Covers protein lookup, variant interpretation, pathway analysis, drug-target associations, and genomic annotation queries. Use when user asks to find protein info, check variant pathogenicity, analyze pathways, find drug targets, or search clinical trials.
metadata:
  mcp-server: biomni-research
  version: 2.0.0
---

# Research Biomedical Databases

## Prerequisites

This skill does nothing on its own. The `biomni-research` MCP server (an Amazon Bedrock AgentCore Gateway) must be deployed on your AWS account and connected to your AI platform first. If it is not connected, none of the tools below exist and no workflow can run.

- **Deployment:** See `mcp-servers/agentcore-gateway/biomni-research-tools/README.md` for full setup. Requires an AWS account with CloudFormation/Lambda/Cognito/IAM/AgentCore permissions, region `us-east-1` or `us-west-2`, and Python 3.12+ with `uv`. Deploy from `agents_catalog/28-Research-agent-biomni-gateway-tools` (`uv sync` → `./scripts/prereq.sh` → `python scripts/agentcore_gateway.py create --name researchapp-gw`). Deploying incurs AWS cost.
- **Platform connection:** See `platforms/` for per-platform guides (Claude Code, Amazon Quick, Kiro, Codex, Strands Agents). MCP-native assistants use the gateway URL directly; header-based setups need a bearer token from `source mcp-servers/agentcore-gateway/biomni-research-tools/get-token.sh researchapp`.
- **Authentication:** Cognito M2M bearer token (60-min expiry). Token refresh varies by platform — see your platform guide.
- **Verify:** Ask the assistant to run `x_amz_bedrock_agentcore_search` with a query like "protein information" — it should return a ranked tool list. Or from the repo: `python agents_catalog/28-Research-agent-biomni-gateway-tools/tests/test_gateway.py --prompt "What proteins interact with TP53?"`.

## Architecture

The Biomni Research Tools are accessed through **Amazon Bedrock AgentCore Gateway** as an MCP server. The gateway exposes 28 database query tools via a single endpoint, with optional **semantic search** to select the most relevant tools per query.

```
User Query
  → AgentCore Gateway (MCP protocol, JWT auth)
    → Semantic search (x_amz_bedrock_agentcore_search) narrows to top-N tools
    → Lambda target executes the selected tool against the external database API
    → Structured results returned
```

The MCP server name is `biomni-research`. All 28 tools are available through this single server.

**Gateway tool naming:** Tools are exposed with a target prefix: `DatabaseLambda___query_uniprot`, `DatabaseLambda___query_clinvar`, etc. When calling tools via the gateway MCP endpoint, use the full prefixed name. In this skill's documentation, tools are referenced by their short name (`query_uniprot`) for readability — prepend `DatabaseLambda___` when invoking via the gateway.

## Decision Tree: Which Workflow to Use

Match the user's question to the right workflow, then read the corresponding reference file for step-by-step tool calls.

| User asks about... | Start with tool | Workflow | Reference |
|---|---|---|---|
| Variant pathogenicity or clinical significance | `query_clinvar` | Variant Interpretation | `references/workflow-variant-interpretation.md` |
| Drug target viability or pharmacology | `query_opentarget` | Drug Target Analysis | `references/workflow-drug-target-analysis.md` |
| Gene role in disease, expression data | `query_geo` or `query_ensembl` | Gene Expression & Phenotype | `references/workflow-gene-expression.md` |
| Protein function, structure, or domains | `query_uniprot` | Protein Analysis | `references/workflow-protein-analysis.md` |
| "What tools can answer X?" or broad question | `x_amz_bedrock_agentcore_search` | Discovery-first | See Semantic Search below |

If unsure which workflow applies, use semantic search first — it returns the most relevant tools for any natural language query.

## Semantic Search: Tool Discovery

The gateway provides a built-in meta-tool for discovering relevant database tools. This is a **gateway-level capability** (not a Lambda-backed database tool) — it's injected automatically by AgentCore Gateway when semantic search is configured. It appears in the MCP tool list alongside the 28 database tools.

Use it when:
- The user's question spans multiple domains
- You're unsure which specific tool to call
- You want to reduce tool-loading overhead

```
Tool: x_amz_bedrock_agentcore_search
Parameter: query (string) — natural language description of what you need
Returns: ranked list of tools with name, description, and inputSchema
```

Example: User asks "tell me about HER2 variant rs1136201"
→ Semantic search returns: `query_ensembl`, `query_gwas_catalog`, `query_clinvar`, `query_dbsnp`
→ Use those tools in sequence rather than loading all 28.

If semantic search is unavailable (gateway configured without `searchType: SEMANTIC`), fall back to selecting tools manually from the Tool Categories table below.

## Tool Categories (28 tools total)

| Category | Tools | Primary use |
|----------|-------|-------------|
| Protein & Structure | `query_uniprot`, `query_alphafold`, `query_interpro`, `query_pdb`, `query_pdb_identifiers`, `query_stringdb`, `query_emdb`, `query_pride` | Protein function, 3D structure, domains, interactions, proteomics |
| Genomic Variants | `query_clinvar`, `query_gnomad`, `query_dbsnp`, `query_ensembl`, `query_ucsc`, `query_gwas_catalog`, `query_regulomedb` | Variant significance, population frequencies, gene models |
| Pathways & Targets | `query_reactome`, `query_opentarget`, `query_monarch`, `query_gtopdb`, `query_openfda`, `query_clinicaltrials` | Pathways, drug-target links, pharmacology, trials |
| Cancer & Expression | `query_cbioportal`, `query_geo` | Tumor mutations, gene expression datasets |
| Specialized | `query_jaspar`, `query_mpd`, `query_synapse`, `query_worms`, `query_paleobiology` | TF motifs, mouse phenotypes, shared datasets, marine species, fossils |

For full parameter schemas for each tool, read `references/tool-parameter-reference.md`.

## Gotchas

- **`query_alphafold` requires `uniprot_id`, NOT a natural language prompt.** You must first get the UniProt accession (e.g., P38398) from `query_uniprot`, then pass it to `query_alphafold`.
- **`query_pdb_identifiers` requires an `identifiers` array** (e.g., `["1ZNI", "4HHB"]`). Use `query_pdb` with a prompt to search; use `query_pdb_identifiers` when you already have PDB IDs.
- **`query_gnomad` has a dedicated `gene_symbol` parameter** — use it directly (e.g., `gene_symbol: "BRCA1"`) for faster, more reliable results than a natural language prompt.
- **`query_opentarget` accepts direct GraphQL** via `query` + `variables` parameters for precise queries. Natural language prompts work for discovery but GraphQL is more reliable for specific target-disease pairs.
- **`query_synapse` datasets may be access-restricted** — if results show `access_restricted: true`, the dataset requires approval through the Synapse web interface and cannot be retrieved programmatically.
- **Identifier formats differ across databases:**
  - UniProt uses accession IDs: P38398, Q9Y6K9
  - Ensembl uses gene IDs: ENSG00000012048
  - Open Targets uses Ensembl gene IDs (NOT HGNC symbols) — convert first via `query_ensembl`
  - gnomAD works best with HGNC gene symbols: BRCA1, TP53
  - ClinVar accepts gene names, variant descriptions, or RS IDs
- **All prompt-based tools accept natural language** but give better results with specificity: include organism ("human"), identifier type, and what information you need.
- **Rate limits may apply** on some databases — if you get 429 errors, space queries or reduce `max_results`.
- **Large result sets for highly-studied genes** (TP53, BRCA1, EGFR) — gnomAD and cBioPortal may return overwhelming responses. Always set `max_results` and use specific queries rather than broad gene-level searches.

## Identifier Cross-Reference Patterns

When chaining tools, you often need to convert between identifier systems:

```
Gene name (BRCA1)
  → query_ensembl → Ensembl ID (ENSG00000012048) → use with query_opentarget
  → query_uniprot → UniProt ID (P38398) → use with query_alphafold
  → use directly with query_gnomad (gene_symbol parameter)
  → use directly with query_clinvar (prompt or search_term)

RS ID (rs80357906)
  → query_dbsnp → gene name, location, alleles
  → query_clinvar → clinical significance
  → query_regulomedb → regulatory impact
  → query_gwas_catalog → trait associations
```

## Open Targets: Gateway vs. Dedicated MCP

Two ways to query Open Targets may exist in your environment:
- **`query_opentarget`** (via Biomni gateway) — natural language or GraphQL, good for quick lookups
- **Dedicated Open Targets MCP server** — full GraphQL access with schema introspection, entity search, batch queries

Use the dedicated Open Targets MCP server when you need complex multi-hop GraphQL queries or schema discovery. Use the gateway's `query_opentarget` for simple target-disease lookups within a larger multi-tool workflow.

## PubMed

PubMed literature search may be available via:
- A **local tool** (`Query_pubmed`) if running the Strands research agent from `agents_catalog/28-Research-agent-biomni-gateway-tools/`
- A **public MCP server** at `https://pubmed.mcp.claude.com/mcp` (no auth required — see `platforms/` for connection)

Use PubMed for:
- Literature searches and systematic reviews
- Finding supporting publications for database findings
- Building evidence summaries with citations

## Error Handling

- **Empty results:** Try alternative identifiers (HGNC symbol → Ensembl ID → UniProt accession). Check for typos in gene names. For variants, try RS ID instead of HGVS notation.
- **Rate limit (429):** Reduce `max_results`, wait 2-3 seconds between consecutive calls to the same database, or switch to a more specific query that returns fewer results.
- **Connection failure / timeout:** Inform the user the gateway is unreachable. Suggest retrying, or use the dedicated Open Targets MCP server as a partial fallback for target/disease queries.
- **Malformed or unexpected response:** Retry with a more specific `prompt` or use the `endpoint` parameter for direct API access instead of natural language translation.

## Limitations

- Tools return database metadata and summaries, not raw data files (e.g., GEO returns dataset descriptions, not expression matrices; PDB returns structure metadata, not coordinate files unless `download: true`)
- No computation capability — cannot run statistical enrichment, GSEA, survival analysis, or variant effect prediction. Use a code interpreter or downstream analysis agent for computation.
- Some datasets require authentication beyond gateway JWT (Synapse access-restricted datasets, private cBioPortal studies)
- Tools query live external APIs — results may differ from published database versions and are subject to API availability
- This skill is for **direct database queries**, not multi-step biomarker discovery workflows. For orchestrated analysis pipelines, use `biomarker-database-analysis` or `biomarker-multi-agent-discovery` instead.

## Conventions

- Default `max_results` to 10 for exploration, up to 50 for comprehensive analysis. Synapse caps at 50.
- Chain queries from broad (identify entity) → specific (get detailed data)
- For variant interpretation, always cross-reference ClinVar (clinical) AND gnomAD (population frequency)
- For drug targets, combine Open Targets (evidence) + STRING (network) + GtoPdb (pharmacology)
- If a tool returns empty results, try alternative identifiers (gene symbol vs. Ensembl ID vs. UniProt accession)
- Cite all database sources using the format: "Database Name (Tool: tool_name). Query: [description]. Retrieved: [date]"
