"""Shared hub access: plain query helpers + Strands @tool wrappers.

Single source of truth so the GT generator and the layer runner do not duplicate
Neptune/Athena access code. Tools mirror the production agent but read all config
from evaluation.config (the eval package stays decoupled from agent/main.py).
"""

from __future__ import annotations

import json
import time

import boto3
from strands import tool

from . import config as C

_neptune = boto3.client("neptune-graph", region_name=C.REGION)
_athena = boto3.client("athena", region_name=C.REGION)

# Live schema discovery from the shared hub_core package (put repo root on path for `python -m`).
import logging as _logging
import os as _os
import sys as _sys

_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _root not in _sys.path:
    _sys.path.insert(0, _root)
try:
    from hub_core.schema import get_hub_schema as _live_get_hub_schema
except Exception:  # noqa: BLE001 — live schema optional; static fallback remains
    _live_get_hub_schema = None
from hub_core.guards import ReadOnlyViolation, reject_mutations, require_select
_log = _logging.getLogger(__name__)


# ── plain helpers (used by the ground-truth generator/verifier) ──────────────
def run_cypher(query: str):
    r = _neptune.execute_query(graphIdentifier=C.GRAPH_ID, queryString=query,
                               language="OPEN_CYPHER")
    return json.loads(r["payload"].read().decode()).get("results", [])


def run_sql(query: str):
    q = _athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": C.ATHENA_DATABASE},
        WorkGroup=C.ATHENA_WORKGROUP,
        ResultConfiguration={"OutputLocation": C.ATHENA_OUTPUT},
    )
    qid = q["QueryExecutionId"]
    while True:
        st = _athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if st in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    if st != "SUCCEEDED":
        raise RuntimeError(f"Athena {st}")
    rows = []
    pag = _athena.get_paginator("get_query_results")
    for page in pag.paginate(QueryExecutionId=qid):
        for row in page["ResultSet"]["Rows"]:
            rows.append([c.get("VarCharValue", "") for c in row["Data"]])
    return rows


# ── Strands tools (used by the L1/L2/L3 agent configurations) ────────────────
@tool
def query_knowledge_graph(cypher_query: str) -> str:
    """Execute an openCypher query against the Neptune Analytics knowledge graph
    (nodes: gene_protein, disease, drug, pathway, ...; edges: drug_protein,
    disease_protein, protein_protein, pathway_protein, ...). Gene nodes are keyed
    by `name`. Note: drug_protein runs gene_protein->drug."""
    try:
        reject_mutations(cypher_query)
    except ReadOnlyViolation as e:
        return f"Rejected (read-only endpoint): {e}"
    results = run_cypher(cypher_query)
    text = json.dumps(results, indent=2, default=str)
    return text[:8000] + "\n... (truncated)" if len(text) > 8000 else text


@tool
def query_patient_data(sql_query: str) -> str:
    """Execute SQL against the TCGA patient data lake via Athena (Parquet, partitioned by
    project_id). Tables: tcga_mutations (ssm_id, chromosome, start_position, end_position,
    reference_allele, tumor_allele, mutation_subtype, hugo_symbol, ensembl_gene_id, aa_change,
    consequence_type, vep_impact, case_id, submitter_id); tcga_expression (sample_id,
    hugo_symbol, entrez_gene_id, value); source_cbioportal / project_id_tcga_* (copy-number).
    Note: patient clinical demographics live on Neptune :case nodes, not in Athena."""
    try:
        require_select(sql_query)
    except ReadOnlyViolation as e:
        return f"Rejected (read-only endpoint): {e}"
    rows = run_sql(sql_query)
    if not rows:
        return "No results."
    out = json.dumps({"columns": rows[0], "rows": rows[1:201]}, indent=2)
    if len(rows) - 1 > 200:
        out += f"\n... ({len(rows)-1} total rows, showing first 200)"
    return out


@tool
def get_hub_schema() -> str:
    """Knowledge graph node/edge types + Athena lake schema — LIVE (Neptune GetGraphSummary + Glue
    get_tables) so onboarded datasets are included; static fallback if introspection is unavailable."""
    if _live_get_hub_schema is not None:
        try:
            return _live_get_hub_schema()
        except Exception as _e:  # noqa: BLE001
            _log.warning("live get_hub_schema failed (%s); using static fallback", _e)
    return _static_hub_schema()


def _static_hub_schema() -> str:
    """Fallback curated static schema — used only if live introspection is unavailable."""
    return (
        "Neptune nodes: gene_protein(27,671; key=name), disease(17,080), drug(7,957), "
        "pathway, biological_process, anatomy, effect_phenotype, molecular_function, "
        "cellular_component, exposure, case(11,428 TCGA patients), sample(33,939).\n"
        "Edges: drug_protein (gene_protein->drug), disease_protein, protein_protein, "
        "pathway_protein, bioprocess_protein, indication, contraindication, drug_effect, "
        "phenotype_protein, case_has_diagnosis, sample_from_case.\n"
        "Gene properties: name, clinvar_pathogenic_count, clinvar_top_significance, cosmic_tier.\n"
        "Disease properties: name, icd10, ncit, mondo_definition.\n"
        "case-node clinical properties (NOT in Athena): age_at_diagnosis, gender, race, "
        "ethnicity, vital_status, days_to_death, primary_diagnosis, project_id.\n"
        "Athena lake (oncology_semantic_hub, Parquet, partitioned by project_id):\n"
        "- tcga_mutations: ssm_id, chromosome, start_position, end_position, reference_allele, "
        "tumor_allele, mutation_subtype, hugo_symbol, ensembl_gene_id, aa_change, "
        "consequence_type, vep_impact, case_id, submitter_id (33 projects, 1.83M rows)\n"
        "- tcga_expression: sample_id, hugo_symbol, entrez_gene_id, value (mRNA z-scores)\n"
        "- source_cbioportal / project_id_tcga_*: copy-number alterations (hugo_symbol, value/cnv_change)"
    )


# name -> tool, for the layer runner to assemble configurations
from .ols_client import ontology_lookup  # noqa: E402

TOOLS = {
    "query_knowledge_graph": query_knowledge_graph,
    "query_patient_data": query_patient_data,
    "get_hub_schema": get_hub_schema,
    "ontology_lookup": ontology_lookup,
}
