"""Oncology Semantic Hub — data-plane MCP server on Amazon Bedrock AgentCore Runtime.

Exposes the hub's READ-ONLY Neptune + Athena tools so any MCP client (Amazon Quick Desktop, Claude
Code, Kiro, or a custom agent) can query the hub over HTTPS+JWT with NO local AWS credentials. The
query + schema logic is shared with the benchmark agent via `hub_core` (single source of truth), and
read-only enforcement uses `hub_core.guards` on top of least-privilege IAM set by deploy.py.

Tool → provenance-tag mapping (for consuming agents/skills that attribute facts):
  query_knowledge_graph   → [Graph]
  query_patient_data      → [Lake:<table>]
  query_variant_annotation→ [RODA:<table>] / [Lake:<table>]
  get_hub_schema          → structural (not a fact source)

Run locally (dev):  PYTHONPATH=/path/to/oncology_semantic_hub python mcp_server.py
On AgentCore Runtime, deploy.py bundles `hub_core` beside this file so `import hub_core` resolves.
"""
from mcp.server.fastmcp import FastMCP

from hub_core import queries as q
from hub_core import schema
from hub_core.guards import ReadOnlyViolation, reject_mutations, require_select

# stateless_http=True + json_response=True are REQUIRED for AgentCore Runtime compatibility.
mcp = FastMCP("oncology-hub-data", host="0.0.0.0", stateless_http=True, json_response=True)  # nosec B104


@mcp.tool()
def query_knowledge_graph(cypher_query: str) -> str:
    """Execute a READ-ONLY openCypher query against the Oncology Semantic Hub Neptune knowledge graph
    (PrimeKG + TCGA case/sample nodes + ClinVar/COSMIC/MONDO enrichments). Attribute results as [Graph].
    Gene/protein nodes are keyed by `name`; for drug targets match `-[:drug_protein]-` UNDIRECTED and
    COUNT(DISTINCT d). For disease-anchored traversals, anchor on the canonical MONDO node
    `(d:disease {mondo:'<CURIE>'})`. Call get_hub_schema first to see labels/edges."""
    try:
        reject_mutations(cypher_query)
    except ReadOnlyViolation as e:
        return f"Rejected (read-only endpoint): {e}"
    return q.run_opencypher(cypher_query)


@mcp.tool()
def query_patient_data(sql_query: str) -> str:
    """Execute READ-ONLY SQL (Athena) over the TCGA patient data lake (tcga_mutations / tcga_expression /
    copy-number). Attribute results as [Lake:<table>]. Always filter partition columns (project_id/source)
    and count patients by COUNT(DISTINCT case_id), samples by COUNT(DISTINCT sample_id)."""
    try:
        require_select(sql_query)
    except ReadOnlyViolation as e:
        return f"Rejected (read-only endpoint): {e}"
    return q.run_athena_sql(sql_query, schema.ATHENA_DATABASE)


@mcp.tool()
def query_variant_annotation(sql_query: str) -> str:
    """Execute READ-ONLY SQL (Athena) over the RODA variant-annotation tables in
    `oncology_semantic_hub_roda` (genoxus_clinvar, civic_evidence, plus any onboarded *_staging).
    Attribute as [RODA:<table>]/[Lake:<table>]; cite CIViC PMIDs (citation_id). Join to the core lake
    with chr-normalization: replace(m.chromosome,'chr','')=g.chrom."""
    try:
        require_select(sql_query)
    except ReadOnlyViolation as e:
        return f"Rejected (read-only endpoint): {e}"
    return q.run_athena_sql(sql_query, schema.RODA_DATABASE)


@mcp.tool()
def get_hub_schema() -> str:
    """Return the LIVE hub schema — Neptune node/edge labels + property names and Athena tables (including
    any onboarded *_staging) + curated query hints. Call this FIRST to discover what is queryable."""
    return schema.get_hub_schema()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
