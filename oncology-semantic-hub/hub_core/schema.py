"""Live hub schema discovery (shared core).

Replaces the hardcoded `get_hub_schema` strings (previously duplicated in
`agentcore/semantic_hub_agent.py` and `evaluation/hub_tools.py`) with LIVE introspection so the
agent always sees the CURRENT hub — including datasets added by the onboarding pipeline — with no
code change:

  • Lake  — AWS Glue `get_tables` over the hub databases → table names + columns/types + partition
    keys. Newly onboarded tables (e.g. `*_staging`) self-surface automatically.
  • Graph — Amazon Neptune Analytics `GetGraphSummary` (DETAILED) → node/edge labels + property names.

A small **curated static preamble** adds the semantics introspection cannot provide (gene key,
MONDO canonical-anchoring discipline, partition-filter conventions, cBioPortal GISTIC codes,
RODA join recipe, biomarker-traversal shape). Structure comes from the catalog; meaning from here.

Config via env (matches the agent): SEMHUB_REGION, SEMHUB_GRAPH_ID, SEMHUB_ATHENA_DB,
SEMHUB_RODA_DB, SEMHUB_RAW_DB. Override the introspected DB list with SEMHUB_SCHEMA_DBS
(comma-separated). Read-only: only Glue/Neptune describe/summary calls.
"""
from __future__ import annotations

import os

import boto3

REGION = os.environ.get("SEMHUB_REGION", "us-west-2")
GRAPH_ID = os.environ.get("SEMHUB_GRAPH_ID", "")
ATHENA_DATABASE = os.environ.get("SEMHUB_ATHENA_DB", "oncology_semantic_hub")
RODA_DATABASE = os.environ.get("SEMHUB_RODA_DB", "oncology_semantic_hub_roda")
RAW_DATABASE = os.environ.get("SEMHUB_RAW_DB", "oncology_semantic_hub_raw")

# Curated semantics that a catalog/graph-summary cannot express. Kept deliberately small.
_CURATED_HINTS = (
    "Query hints (curated):\n"
    "- Graph: gene/protein nodes are keyed by `name` — match `(g:gene_protein {name:'EGFR'})`. "
    "For drug targets use `-[:drug_protein]-` UNDIRECTED and COUNT(DISTINCT d).\n"
    "- Disease anchoring: a disease NAME fans out to many subtype nodes (non-reproducible counts). "
    "Resolve the disease with ontology_lookup to its MONDO CURIE and anchor on the single node "
    "carrying it: `(d:disease {mondo:'<CURIE>'})`; traverse UNDIRECTED + COUNT(DISTINCT ...).\n"
    "- Clinical demographics (age_at_diagnosis, gender, race, vital_status, days_to_death, "
    "primary_diagnosis) live on graph `case` nodes, NOT in Athena.\n"
    "- Athena: partition columns (e.g. project_id/source) are FILTERABLE — ALWAYS filter. Count "
    "patients by COUNT(DISTINCT case_id), samples by COUNT(DISTINCT sample_id).\n"
    "- cBioPortal copy-number table: `value` is a GISTIC code (2=high-level amplification, 1=gain, "
    "0=diploid, -1=shallow deletion, -2=deep deletion) — amplification questions come from THIS "
    "table (value=2), not the mutations table. Its project_id uses cBioPortal ids ('gbm_tcga') which "
    "DIFFER from GDC ids ('TCGA-GBM') for the same cohort.\n"
    "- RODA variant annotation (database " + RODA_DATABASE + "): join to the core lake with "
    "chr-normalization — `JOIN ... ON replace(m.chromosome,'chr','')=g.chrom AND m.start_position=g.pos "
    "AND m.reference_allele=g.ref AND m.tumor_allele=g.alt`. Genoxus/ClinVar germline significance is "
    "NOT somatic driver status; for somatic actionability use CIViC (evidence_level A-E) and cite the "
    "PMID (citation_id). SNVs match exactly; indels may differ.\n"
    "- Biomarker actionability (ta_oncology graph extension): traverse "
    "`(g:gene_protein)<-[:BIOMARKER_OF_GENE]-(:CancerBiomarker)-[:PREDICTS_RESPONSE_TO]->(d:drug)`."
)


def _databases() -> list[str]:
    """Databases to introspect for the lake section. SEMHUB_SCHEMA_DBS overrides; default is the
    L3 data plane (core + RODA). The raw flat-PrimeKG DB is excluded by default (L2-only) to keep
    the L3 schema clean — add it via SEMHUB_SCHEMA_DBS if a deployment needs it."""
    override = os.environ.get("SEMHUB_SCHEMA_DBS")
    if override:
        return [d.strip() for d in override.split(",") if d.strip()]
    return [d for d in (ATHENA_DATABASE, RODA_DATABASE) if d]


def _glue_client():
    return boto3.client("glue", region_name=REGION)


def _neptune_client():
    return boto3.client("neptune-graph", region_name=REGION)


def _lake_schema(glue=None) -> str:
    """Live Athena/Glue schema across the hub databases (auto-includes onboarded tables)."""
    glue = glue or _glue_client()
    blocks: list[str] = []
    for db in _databases():
        try:
            tables: list[dict] = []
            for page in glue.get_paginator("get_tables").paginate(DatabaseName=db):
                tables += page.get("TableList", [])
        except Exception as e:  # db missing / access denied — skip, don't fail the whole schema
            blocks.append(f"Athena database `{db}`: unavailable ({e.__class__.__name__})")
            continue
        if not tables:
            continue
        lines = [f"Athena database `{db}` ({len(tables)} tables):"]
        for t in sorted(tables, key=lambda x: x.get("Name", "")):
            sd = t.get("StorageDescriptor", {}) or {}
            cols = ", ".join(f"{c['Name']}:{c['Type']}" for c in sd.get("Columns", []) or [])
            line = f"  - {t.get('Name')}({cols})"
            parts = t.get("PartitionKeys", []) or []
            if parts:
                line += " | partitions: " + ", ".join(f"{p['Name']}:{p['Type']}" for p in parts)
            lines.append(line)
        blocks.append("\n".join(lines))
    return "\n".join(blocks) if blocks else "(no Athena tables discovered)"


def _graph_schema(neptune=None) -> str:
    """Live Neptune Analytics node/edge labels + property names via GetGraphSummary."""
    if not GRAPH_ID:
        return "(Neptune graph not configured: set SEMHUB_GRAPH_ID)"
    neptune = neptune or _neptune_client()
    try:
        summary = neptune.get_graph_summary(graphIdentifier=GRAPH_ID, mode="DETAILED")
        g = summary.get("graphSummary", {})
    except Exception as e:
        return f"(Neptune schema unavailable: {e.__class__.__name__})"
    # nodeProperties/edgeProperties are lists of single-key {name: count} dicts.
    nprops = sorted({k for d in g.get("nodeProperties", []) for k in d})
    eprops = sorted({k for d in g.get("edgeProperties", []) for k in d})
    return (
        f"Neptune graph `{GRAPH_ID}` — {g.get('numNodes', '?')} nodes, {g.get('numEdges', '?')} edges.\n"
        f"Node labels: {', '.join(g.get('nodeLabels', []))}\n"
        f"Edge labels: {', '.join(g.get('edgeLabels', []))}\n"
        f"Node properties: {', '.join(nprops)}\n"
        f"Edge properties: {', '.join(eprops)}"
    )


def get_hub_schema() -> str:
    """Return the LIVE hub schema: Neptune graph labels/properties + Athena tables (incl. any
    onboarded `*_staging`) + curated query hints. Reflects the current hub with no hardcoded schema,
    so newly onboarded datasets are always reachable by the agent."""
    return f"{_graph_schema()}\n\n{_lake_schema()}\n\n{_CURATED_HINTS}"


if __name__ == "__main__":
    print(get_hub_schema())
