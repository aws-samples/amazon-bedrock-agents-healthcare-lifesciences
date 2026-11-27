"""Oncology Semantic Hub — Strands agent on Bedrock AgentCore Runtime (L3 = full hub).

Self-contained entrypoint (no relative-package imports) so it runs in the Runtime container.
Tools: query_knowledge_graph (Neptune openCypher), query_patient_data (Athena SQL),
get_hub_schema, ontology_lookup (deployed OLS MCP server via SSM/Cognito). Configuration is read
from environment variables (set by deploy.py) with sensible defaults.

Observability: deployed with `opentelemetry-instrument` so traces/spans land in CloudWatch for
AgentCore Evaluations (Correctness / Faithfulness / ToolSelectionAccuracy).
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _safe_urlopen(req_or_url, **kwargs):
    """urllib.request.urlopen, restricted to https:// (Bandit B310 — avoid file:/custom schemes).
    These URLs come from SSM params / env vars we control, never end-user input, but validating the
    scheme is the cheap, correct hardening B310 asks for rather than suppressing the finding."""
    url = req_or_url.full_url if isinstance(req_or_url, urllib.request.Request) else req_or_url
    scheme = urllib.parse.urlsplit(url).scheme
    if scheme != "https":
        raise ValueError(f"refusing to open non-https URL (scheme={scheme!r}): {url}")
    return urllib.request.urlopen(req_or_url, **kwargs)  # nosec B310 — scheme validated above


REGION = os.environ.get("SEMHUB_REGION", "us-west-2")
GRAPH_ID = os.environ.get("SEMHUB_GRAPH_ID", "")  # injected by deploy.py; required at runtime
ATHENA_DATABASE = os.environ.get("SEMHUB_ATHENA_DB", "oncology_semantic_hub")
ATHENA_WORKGROUP = os.environ.get("SEMHUB_ATHENA_WG", "primary")
ATHENA_OUTPUT = os.environ.get("SEMHUB_ATHENA_OUTPUT", "")  # injected by deploy.py (s3://<bucket>/athena-results/)
RODA_DATABASE = os.environ.get("SEMHUB_RODA_DB", "oncology_semantic_hub_roda")
RAW_DATABASE = os.environ.get("SEMHUB_RAW_DB", "oncology_semantic_hub_raw")  # L2 flat PrimeKG (no graph)
SUBJECT_MODEL_ID = os.environ.get("SEMHUB_SUBJECT_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
OLS_SSM_PREFIX = os.environ.get("SEMHUB_OLS_SSM_PREFIX", "/app/ontology-lookup-service/agentcore")
# Hybrid-search knowledge base (semantic recall over TCGA descriptions + PubMed abstracts).
KB_ID_ENV = os.environ.get("SEMHUB_KB_ID")  # optional explicit override
KB_ID_SSM = os.environ.get("SEMHUB_KB_ID_SSM", "/app/oncology-hub/knowledge_base/kb_id")

app = BedrockAgentCoreApp()
_neptune = boto3.client("neptune-graph", region_name=REGION)
_athena = boto3.client("athena", region_name=REGION)
_kb_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
_ols_cfg: dict = {}
_kb_cfg: dict = {}

# Live hub-schema discovery lives in the shared hub_core package (bundled into the deployment
# package by deploy.py). Resolve it whether running locally from agentcore/ (hub_core is one dir
# up) or from the deployment package root (hub_core sits beside this file).
import sys as _sys
_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.dirname(_here)):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
from hub_core.schema import get_hub_schema as _live_get_hub_schema
from hub_core import queries as _q
from hub_core.guards import ReadOnlyViolation, reject_mutations, require_select


# ── tools ────────────────────────────────────────────────────────────────────
@tool
def get_hub_schema() -> str:
    """Return the knowledge graph node/edge types + Athena lake schema, discovered LIVE from Neptune
    (GetGraphSummary) and Glue (get_tables) at call time — so newly onboarded datasets are always
    included. Falls back to a curated static snapshot only if live introspection fails."""
    try:
        return _live_get_hub_schema()
    except Exception as _e:  # noqa: BLE001 — never fail the tool; degrade to the static snapshot
        logger.warning("live get_hub_schema failed (%s); using static fallback", _e)
        return _static_hub_schema()


def _static_hub_schema() -> str:
    """Fallback curated static schema — used only if live Glue/Neptune introspection fails."""
    return (
        "Neptune nodes: gene_protein(27,671; key=name), disease(17,080), drug(7,957), pathway, "
        "biological_process, anatomy, effect_phenotype, molecular_function, cellular_component, "
        "exposure, case(11,428 TCGA patients), sample(33,939).\n"
        "Edges: drug_protein (gene_protein->drug), disease_protein, protein_protein, pathway_protein, "
        "bioprocess_protein, indication, contraindication, drug_effect, case_has_diagnosis, sample_from_case.\n"
        "Gene properties: name, clinvar_pathogenic_count, cosmic_tier. Disease properties: name, icd10, ncit, mondo (canonical MONDO CURIE on key oncology diseases — anchor disease traversals to the ONE node carrying it).\n"
        "case-node clinical properties (NOT in Athena): age_at_diagnosis, gender, vital_status, days_to_death, primary_diagnosis.\n"
        "Athena lake (Parquet) — patient data from TWO sources across many cancer types:\n"
        "- tcga_mutations (GDC/TCGA somatic mutations; 33 TCGA cancer types): ssm_id, chromosome, "
        "start_position, end_position, reference_allele, tumor_allele, mutation_subtype, hugo_symbol, "
        "ensembl_gene_id, aa_change, consequence_type, vep_impact, case_id, submitter_id; partition project_id "
        "(GDC ids like 'TCGA-GBM','TCGA-LUAD').\n"
        "- tcga_expression (gene expression): sample_id, hugo_symbol, entrez_gene_id, value; partitions "
        "source, project_id (source='cbioportal').\n"
        "- source_cbioportal (cBioPortal copy-number/CNA; ~5,490 samples across 10 cohorts): sample_id, "
        "hugo_symbol, entrez_gene_id, value; partition project_id using cBioPortal study ids "
        "('gbm_tcga','brca_tcga','luad_tcga' …) — these differ from GDC's 'TCGA-GBM' (same cohorts, different "
        "identifiers; resolve with ontology_lookup / note the mapping). `value` is an INTEGER GISTIC "
        "copy-number code: 2=high-level amplification, 1=gain, 0=diploid, -1=shallow deletion, -2=deep "
        "deletion (use value=2 for amplification — copy-number/amplification questions come from THIS table, "
        "not tcga_mutations).\n"
        "Athena query patterns (partition columns project_id/source are FILTERABLE — always filter; count "
        "patients by case_id, samples by sample_id):\n"
        "  SELECT hugo_symbol, count(DISTINCT case_id) AS n FROM tcga_mutations WHERE project_id='TCGA-GBM' "
        "AND hugo_symbol IN ('PTEN','EGFR') GROUP BY hugo_symbol ORDER BY n DESC\n"
        "  -- pan-cancer breadth: SELECT project_id, count(DISTINCT case_id) n FROM tcga_mutations "
        "WHERE hugo_symbol='EGFR' GROUP BY project_id ORDER BY n DESC\n"
        "  -- cBioPortal CNA amplification: SELECT count(DISTINCT sample_id) FROM source_cbioportal "
        "WHERE project_id='gbm_tcga' AND hugo_symbol='EGFR' AND value=2\n"
        "RODA variant-annotation extension (L3; database oncology_semantic_hub_roda — use query_variant_annotation):\n"
        "- genoxus_clinvar (ClinVar by GRCh38 position; germline AND somatic/oncogenicity classifications): "
        "chrom (no 'chr'), pos, ref, alt, gene_symbol, clinical_significance, review_status, conditions. "
        "Annotate cohort by JOIN oncology_semantic_hub.tcga_mutations m ON replace(m.chromosome,'chr','')=chrom "
        "AND m.start_position=pos AND m.reference_allele=ref AND m.tumor_allele=alt. Germline ClinVar is NOT "
        "somatic driver status; SNVs match exactly, indels may differ.\n"
        "- civic_evidence (CIViC SOMATIC actionability): gene, variant, disease, doid, therapies(array), "
        "evidence_level (A-E), significance, citation_id (PMID), evidence_civic_url. Cite the PMID.\n"
        "Graph extension ta_oncology (in Neptune — use query_knowledge_graph): "
        "(g:gene_protein)<-[:BIOMARKER_OF_GENE]-(b:CancerBiomarker {partition:'ta_oncology'})"
        "-[r:PREDICTS_RESPONSE_TO {direction,evidence_level,pmid}]->(d:drug) — traverse gene->biomarker->drug "
        "for actionable somatic biomarkers."
    )


@tool
def query_knowledge_graph(cypher_query: str) -> str:
    """Execute an openCypher query against the Neptune Analytics knowledge graph. Gene nodes are keyed by
    `name`. For drug-gene target relationships, match `(g:gene_protein {name:'X'})-[:drug_protein]-(d:drug)`
    UNDIRECTED (use `-[:drug_protein]-`, not a directed arrow) and count DISTINCT d. The ta_oncology
    CancerBiomarker extension is only for biomarker-actionability / predicts-response questions, not for
    plain drug-target relationships.

    DISEASE-anchored traversals (genes / interaction partners / pathway members associated with a disease):
    a disease NAME fans out to many subtype nodes and gives non-reproducible counts. Instead, resolve the
    disease with ontology_lookup to its MONDO id and anchor on the single canonical node
    `(d:disease {mondo:'<CURIE>'})`; traverse UNDIRECTED and COUNT(DISTINCT ...)."""
    try:
        reject_mutations(cypher_query)
    except ReadOnlyViolation as e:
        return f"Rejected (read-only endpoint): {e}"
    return _q.run_opencypher(cypher_query, graph_id=GRAPH_ID)


def _run_athena(sql_query: str, database: str) -> str:
    """Run an Athena query in `database` via the shared hub_core executor (thin shim; single source).
    Read-only guard applied here so every SQL tool (patient / variant / primekg) rejects non-SELECT in
    process — parity with the MCP server; the agent's IAM role is read-only too (defense-in-depth)."""
    try:
        require_select(sql_query)
    except ReadOnlyViolation as e:
        return f"Rejected (read-only endpoint): {e}"
    return _q.run_athena_sql(sql_query, database, workgroup=ATHENA_WORKGROUP, output=ATHENA_OUTPUT)


@tool
def query_patient_data(sql_query: str) -> str:
    """Execute SQL against the TCGA patient data lake via Athena (tcga_mutations / tcga_expression /
    copy-number). Clinical demographics are on Neptune :case nodes, not in Athena."""
    return _run_athena(sql_query, ATHENA_DATABASE)


@tool
def query_variant_annotation(sql_query: str) -> str:
    """Execute SQL (Athena) over the RODA variant-annotation tables in `oncology_semantic_hub_roda` (L3-only):
    - `genoxus_clinvar`: ClinVar classifications by GRCh38 position (germline AND somatic/oncogenicity) —
      chrom (no 'chr'), pos, ref, alt, gene_symbol, clinical_significance, review_status, conditions.
    - `civic_evidence`: CIViC SOMATIC clinical actionability — gene, variant, disease, doid, therapies (array),
      evidence_level (A-E), significance, citation_id (PMID), evidence_civic_url.
    To annotate the cohort, JOIN to the core lake with fully-qualified names + chr-normalization:
      SELECT g.clinical_significance, count(DISTINCT m.case_id) n
      FROM oncology_semantic_hub.tcga_mutations m JOIN oncology_semantic_hub_roda.genoxus_clinvar g
        ON replace(m.chromosome,'chr','')=g.chrom AND m.start_position=g.pos
       AND m.reference_allele=g.ref AND m.tumor_allele=g.alt
      WHERE m.project_id='TCGA-GBM' AND m.hugo_symbol='EGFR' GROUP BY 1
    Genoxus ClinVar is *annotation*: germline significance is NOT somatic driver status — for somatic
    actionability use civic_evidence (cite the PMID). SNVs match exactly; indel ref/alt may differ."""
    return _run_athena(sql_query, RODA_DATABASE)


@tool
def query_primekg(sql_query: str) -> str:
    """Execute SQL (Athena) over RAW, FLAT PrimeKG in `oncology_semantic_hub_raw` (L2 raw-data layer —
    there is NO graph traversal here; you must self-join with SQL):
    - `primekg_edges` (PARTITIONED BY `relation` — ALWAYS filter `relation=...` to prune the scan):
      columns relation, display_relation, x_index, x_id, x_type, x_name, x_source, y_index, y_id, y_type,
      y_name, y_source. Edges are stored BOTH directions, so match either the x or y side. Key relations:
      'drug_protein' (drug<->gene/protein), 'disease_protein', 'indication'/'contraindication'/'off-label use'
      (drug<->disease), 'pathway_protein', 'protein_protein', 'disease_phenotype_positive',
      'bioprocess_protein', 'molfunc_protein', 'cellcomp_protein'.
    - `primekg_nodes`: index, id, type, name, source.
    Example — drugs targeting EGFR (check both directions):
      SELECT DISTINCT d FROM (
        SELECT y_name d FROM primekg_edges WHERE relation='drug_protein' AND x_name='EGFR'
        UNION SELECT x_name d FROM primekg_edges WHERE relation='drug_protein' AND y_name='EGFR')
    These are the same facts a knowledge graph would hold, but flat — reconcile identifiers yourself; there
    is no ontology service."""
    return _run_athena(sql_query, RAW_DATABASE)


def _ols_config() -> dict:
    if _ols_cfg:
        return _ols_cfg
    ssm = boto3.client("ssm", region_name=REGION)
    names = ["mcp_url", "cognito_token_url", "machine_client_id", "cognito_secret", "cognito_auth_scope"]
    p = {n: ssm.get_parameter(Name=f"{OLS_SSM_PREFIX}/{n}", WithDecryption=True)["Parameter"]["Value"] for n in names}
    form = {"grant_type": "client_credentials", "client_id": p["machine_client_id"], "client_secret": p["cognito_secret"]}
    if p.get("cognito_auth_scope"):
        form["scope"] = p["cognito_auth_scope"]
    req = urllib.request.Request(p["cognito_token_url"], data=urllib.parse.urlencode(form).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    _ols_cfg.update(url=p["mcp_url"], token=json.load(_safe_urlopen(req, timeout=25))["access_token"])
    return _ols_cfg


async def _ols_search(query: str, ontology: str):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    c = _ols_config()
    async with streamablehttp_client(url=c["url"], headers={"Authorization": f"Bearer {c['token']}"}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("search_terms", {"query": query, "ontology": ontology})
            return res.content[0].text if res.content else ""


@tool
def ontology_lookup(query: str, ontology: str = "mondo") -> str:
    """Resolve a disease/gene/phenotype term to its authoritative ontology id (e.g. MONDO CURIE)
    via the EBI Ontology Lookup Service. Use for ontology-id questions and to reconcile TCGA<->graph
    identifier mismatches. Returns top matches as JSON: id (CURIE), label."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            raw = ex.submit(lambda: asyncio.run(_ols_search(query, ontology))).result(timeout=90)
        items = json.loads(raw).get("items", [])[:5]
        return json.dumps([{"id": (it.get("iri", "").rstrip("/").split("/")[-1].replace("_", ":", 1)),
                            "label": it.get("label")} for it in items])
    except Exception as e:
        return f"OLS lookup failed: {e}"


def _kb_id() -> str:
    """Resolve the knowledge base id (env override → SSM), cached per warm container."""
    if _kb_cfg.get("id"):
        return _kb_cfg["id"]
    kid = KB_ID_ENV
    if not kid:
        ssm = boto3.client("ssm", region_name=REGION)
        kid = ssm.get_parameter(Name=KB_ID_SSM)["Parameter"]["Value"]
    _kb_cfg["id"] = kid
    return kid


@tool
def knowledge_search(query: str, source: str = "", min_year: int = 0,
                     disease: str = "", max_results: int = 5) -> str:
    """Semantic recall over the hub's literature + study-description knowledge base (all 33 TCGA
    project descriptions + curated PubMed abstracts on glioblastoma/EGFR and immune-checkpoint
    resistance). Use this FIRST for questions about published evidence, prior findings, or
    "which studies/cohorts are relevant to X" — it retrieves by meaning, not keywords.

    Returns JSON passages each with a structured `citation` you MUST reuse verbatim (PubMed →
    PMID; TCGA → project_id). Optional filters: source ("PubMed" or "TCGA"); min_year (e.g. 2020,
    PubMed only); disease (e.g. "glioblastoma") — added to the semantic query to focus recall.

    IMPORTANT: cite ONLY sources returned here. If results are empty, say no supporting evidence was
    found in the knowledge base — never invent a PMID or study."""
    return _kb_search(query, source=source, min_year=min_year, disease=disease, max_results=max_results)


def _kb_search(query: str, source: str = "", min_year: int = 0,
               disease: str = "", max_results: int = 5) -> str:
    """Core knowledge-base retrieval + citation formatting (plain function; unit-testable)."""
    text = f"{query} disease: {disease}" if disease else query
    filters = []
    if source:
        filters.append({"equals": {"key": "source", "value": source}})
    if min_year:
        filters.append({"greaterThanOrEquals": {"key": "year", "value": int(min_year)}})
    vcfg = {"numberOfResults": max(1, min(int(max_results), 10))}
    if len(filters) == 1:
        vcfg["filter"] = filters[0]
    elif len(filters) > 1:
        vcfg["filter"] = {"andAll": filters}
    try:
        resp = _kb_runtime.retrieve(
            knowledgeBaseId=_kb_id(),
            retrievalQuery={"text": text},
            retrievalConfiguration={"vectorSearchConfiguration": vcfg})
    except Exception as e:  # noqa: BLE001
        return f"knowledge_search failed: {e}"
    results = []
    for it in resp.get("retrievalResults", []):
        md = it.get("metadata", {}) or {}
        src = md.get("source")
        snippet = (it.get("content", {}) or {}).get("text", "") or ""
        rec = {"score": round(float(it.get("score", 0)), 3), "text": snippet[:600]}
        if src == "PubMed":
            pmid = md.get("pmid")
            year = md.get("year")
            try:
                year = int(year)
            except (TypeError, ValueError):
                pass
            rec.update(source="PubMed", pmid=pmid, title=md.get("title"),
                       citation=f"{md.get('title')} ({md.get('journal')}, {year}) — PMID:{pmid}",
                       url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
        elif src == "TCGA":
            pid = md.get("project_id")
            rec.update(source="TCGA", project_id=pid, disease=md.get("disease"),
                       citation=f"{pid} — {md.get('disease')} (TCGA project)",
                       url=f"https://portal.gdc.cancer.gov/projects/{pid}")
        else:
            rec["source"] = src or "unknown"
        results.append(rec)
    if not results:
        return json.dumps({"results": [], "note": "No relevant sources found in the knowledge base."})
    return json.dumps({"results": results}, default=str)


_L3_PROMPT = """You are an oncology biomarker research assistant with access to a semantic hub:
a semantic knowledge base (vector recall over TCGA project descriptions + curated PubMed abstracts),
a Neptune knowledge graph (genes, diseases, drugs, pathways; TCGA patient nodes), a TCGA Athena data
lake (mutations/expression/copy-number), and an OLS ontology-resolution tool.

Tools:
- knowledge_search: semantic recall over literature + study descriptions. Call it FIRST for questions
  about published evidence, prior work, or "which studies/cohorts relate to X".
- get_hub_schema: graph/lake schema (call before writing graph/SQL).
- query_knowledge_graph: openCypher on Neptune (see the tool's docstring for drug-target query guidance).
- query_patient_data: Athena SQL over TCGA mutations/expression/copy-number.
- query_variant_annotation: Athena SQL over the RODA variant tables (genoxus_clinvar = ClinVar annotation by
  position; civic_evidence = CIViC SOMATIC actionability with evidence levels A-E + PMIDs). Traverse the
  ta_oncology CancerBiomarker->drug extension via query_knowledge_graph.
- ontology_lookup: authoritative MONDO/ontology ids; prefer it for identifier resolution over the
  graph's stored mapping (which can be wrong/approximate).

HYBRID SEARCH — for literature/evidence or study-discovery questions, chain the tools: (1) knowledge_search
to recall relevant abstracts/cohorts by meaning; (2) extract key entities (genes, diseases) from the
recalled passages and resolve them to canonical ids with ontology_lookup; (3) use those ids for precise
facts via query_knowledge_graph / query_patient_data; (4) answer, CITING the exact sources returned by
knowledge_search (PubMed PMIDs / TCGA project ids).

Citation discipline: cite a PMID/TCGA id ONLY if knowledge_search actually returned it; do NOT fabricate a
citation. If a fact comes from your own knowledge, still answer but tag it [Model knowledge] instead of inventing a source.

PROVENANCE (make every answer auditable and easy to trace) — you MUST place an inline bracket tag
IMMEDIATELY AFTER EVERY fact / number / name, in the SAME sentence. Inline bracket tagging is REQUIRED and
is the PRIMARY provenance mechanism; a trailing prose "sources" paragraph does NOT satisfy it. Never present
a number, gene, drug, or claim without its bracket tag right next to it.
Use these EXACT bracket forms (not prose descriptions):
- `[KB PMID:xxxxx]` or `[KB TCGA-XXX]` — recalled from the knowledge base (use the real citation from knowledge_search)
- `[Graph]` — a relationship / druggability / pathway fact from the Neptune knowledge graph
- `[Lake:<table>]` — a patient/cohort number from the Athena data lake (name the table, e.g. [Lake:tcga_mutations])
- `[OLS:CURIE]` — an identifier you resolved via ontology_lookup
- `[Model knowledge]` — a fact from your own training, not a tool; use this (with your best answer) instead of refusing when no tool has the fact
FORMAT RULE — required inline form: write "82 TCGA-GBM patients carry an EGFR mutation [Lake:tcga_mutations]."
Do NOT write "82 patients (Data lake: tcga_mutations)", do NOT describe the source only in a later prose
paragraph, and do NOT leave any tool-derived number/name untagged. Every sentence stating a tool-derived
fact ends with its `[...]` tag.
You MAY additionally end with a brief **"Sources & provenance"** summary (knowledge base / knowledge graph /
data lake), but ONLY in addition to the inline tags — never as a replacement for them.

STATISTICS: for co-occurrence / mutual-exclusivity / significance questions, first retrieve the EXACT
contingency table (counts + denominators, with provenance), then give your best answer. If you estimate a
p-value or significance from your own reasoning rather than a deterministic tool, label it [Model knowledge]
so the provenance stays honest. Do not refuse to answer.

Answer with specific numbers, names, and ontology ids from tool outputs. For an ontology-id question,
call ontology_lookup and report the exact CURIE. If the requested data is NOT in the hub (e.g. tumor
stage, protein abundance, imaging, treatment/response, or a gene absent from the graph), note the hub does
not contain it and give your best answer from your own knowledge tagged [Model knowledge] — do NOT refuse;
but never fabricate a tool source or citation."""

_L1_PROMPT = """You are a biomedical research assistant connected to a TCGA data lake via Athena SQL
ONLY. Tool: query_patient_data (tables tcga_mutations, tcga_expression, copy-number; partitioned by
project_id). You do NOT have a knowledge graph, ontology service, or any curated mappings between
identifiers, drugs, pathways, or diseases, and no patient clinical demographics.

Answer using SQL over these tables plus your own knowledge. If a question needs information not in
these tables (which drugs target a gene, gene-pathway or disease-gene relationships, ontology
identifiers like MONDO, or patient age/stage/survival), note the lake does not contain it and give your best
answer from your own knowledge instead — do NOT refuse. Give exact numbers, gene names, and counts when the
tables support them.
PROVENANCE (REQUIRED, inline): put a bracket tag IMMEDIATELY AFTER every fact, in the SAME sentence —
`[Lake:<table>]` for a lake number (required form: "82 TCGA-GBM patients carry an EGFR mutation
[Lake:tcga_mutations]") and `[Model knowledge]` for own-knowledge facts. Never leave a number/name untagged
and never describe the source only in prose. You MAY add a one-line lake-vs-own-knowledge note in addition to
the inline tags, never instead of them."""

_L2_PROMPT = """You are a biomedical research assistant with access to a RAW DATA LAKE (Athena SQL) and a
literature knowledge base — but NO knowledge graph and NO ontology service. You must join and reconcile
identifiers yourself across flat tables.

Tools:
- query_patient_data: Athena SQL over the TCGA lake (tcga_mutations / tcga_expression / copy-number; cBioPortal source_cbioportal).
- query_variant_annotation: Athena SQL over the RODA variant tables in oncology_semantic_hub_roda
  (genoxus_clinvar = ClinVar annotation by GRCh38 position; civic_evidence = CIViC SOMATIC actionability,
  evidence_level A-E + PMIDs). FLAT tables — no graph.
- query_primekg: Athena SQL over FLAT PrimeKG in oncology_semantic_hub_raw (primekg_edges PARTITIONED BY
  `relation` — ALWAYS filter relation; edges stored BOTH directions; primekg_nodes). Same biomedical
  knowledge a graph would hold, but you must self-join it with SQL (drug_protein=gene<->drug,
  disease_protein, indication/contraindication, pathway_protein, protein_protein, ...).
- knowledge_search: semantic recall over literature + study descriptions (PubMed abstracts, TCGA study text).
  Cite a PMID/TCGA id only if knowledge_search returned it; do not fabricate one — tag own-knowledge facts [Model knowledge].

You do NOT have a traversable knowledge graph, an ontology-resolution service (OLS), or curated identifier
mappings. Resolve identifiers with SQL joins + your own knowledge; for an authoritative ontology id
(MONDO/etc.) you can only use your own knowledge or the flat data — say so if you cannot determine it.

Answer using the tools plus your own knowledge. If a fact is not in these tables + KB, give your best answer from your own knowledge tagged [Model knowledge]
rather than refusing. Give exact numbers, names, and counts from tool output.

PROVENANCE (REQUIRED, inline): put a bracket tag IMMEDIATELY AFTER every fact, in the SAME sentence — one of
`[Lake:<table>]`, `[RODA:<table>]`, `[PrimeKG-flat:<relation>]`, `[KB PMID:xxxxx]`, `[Model knowledge]`
(own training, when no tool has it — still answer, just tag it). Required inline form:
"82 TCGA-GBM patients carry an EGFR mutation [Lake:tcga_mutations]." Never present a number/name without its
bracket tag right next to it, and do NOT put the source only in a later prose paragraph. You MAY additionally
end with a short "Sources & provenance" summary, but only in addition to the inline tags, never instead.

STATISTICS: retrieve the exact contingency table (counts + denominators) with provenance, then give your
best answer; if you estimate a statistic from your own reasoning rather than a deterministic tool, label it
[Model knowledge]. Do not refuse to answer."""

_L0_PROMPT = """You are a biomedical research assistant answering entirely from your own trained (parametric)
knowledge. You have no data tools. Answer EVERY question with your best, most specific answer — gene names, drugs,
mechanisms, and your best numeric estimate — drawing on what you learned from the literature, including TCGA and
oncology publications. Commit to a concrete answer; do NOT refuse, defer, or say you lack data access. If you are
uncertain, still give your single most likely answer and briefly note it is an estimate.

PROVENANCE (for auditability): you have NO data tools, so tag every factual claim by its basis —
`[Model knowledge]` for general training knowledge, or `[Recalled: <source>]` for a specific paper/finding
you remember (mark it recalled, NOT retrieved). Do NOT use tool tags ([Lake]/[Graph]/[KB]/[OLS]); you have
no such tools. End with a one-line note that all answers come from model knowledge, not retrieval."""

_ws_cfg: dict = {}


def _ws_config() -> dict:
    """OAuth token + gateway URL for the AWS-managed Web Search Tool (AgentCore Gateway, us-east-1).
    Config via env (set by deploy.py for L0-web): SEMHUB_WS_GATEWAY_URL / _TOKEN_URL / _CLIENT_ID /
    _CLIENT_SECRET / _SCOPE."""
    if _ws_cfg:
        return _ws_cfg
    form = {"grant_type": "client_credentials",
            "client_id": os.environ["SEMHUB_WS_CLIENT_ID"],
            "client_secret": os.environ["SEMHUB_WS_CLIENT_SECRET"]}
    if os.environ.get("SEMHUB_WS_SCOPE"):
        form["scope"] = os.environ["SEMHUB_WS_SCOPE"]
    req = urllib.request.Request(os.environ["SEMHUB_WS_TOKEN_URL"],
                                 data=urllib.parse.urlencode(form).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    _ws_cfg.update(url=os.environ["SEMHUB_WS_GATEWAY_URL"],
                   token=json.load(_safe_urlopen(req, timeout=25))["access_token"])
    return _ws_cfg


async def _ws_search(query: str):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    c = _ws_config()
    async with streamablehttp_client(url=c["url"], headers={"Authorization": f"Bearer {c['token']}"}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("web-search-tool___WebSearch", {"query": query, "maxResults": 5})
            return res.content[0].text if res.content else ""


@tool
def web_search(query: str) -> str:
    """Search the public web via the AWS-managed Web Search Tool (AgentCore Gateway) for general/published
    knowledge (literature, drug labels, gene/disease facts). Returns top result snippets with source URLs.
    Cite each retrieved fact as [Web:<url>]; do not fabricate URLs."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            raw = ex.submit(lambda: asyncio.run(_ws_search(query))).result(timeout=75)
        data = json.loads(raw)
        out = [f"[Web:{r.get('url', '')}] {r.get('title', '')}: {str(r.get('text', ''))[:250]}"
               for r in data.get("results", [])[:5]]
        return "\n".join(out) or "no web results found"
    except Exception as e:
        return f"web_search unavailable: {e}"

_L0WEB_PROMPT = """You are a biomedical research assistant with ONE tool: web_search (public web). You have NO
data lake, knowledge graph, or ontology service. For any public/general fact, CALL web_search and ground the
answer in the returned results, citing [Web:<url>]. If web_search returns nothing useful, answer from your own
training and tag it [Model knowledge]. Never fabricate a URL or a database result. End with a short provenance
note (web sources used vs model knowledge)."""

LAYER = os.environ.get("SEMHUB_LAYER", "L3")
assert LAYER in {"L0", "L0-web", "L1", "L2", "L3", "L3a", "L3b", "L3_no_graph", "L3_no_ols", "L3_no_kb"}, f"unknown SEMHUB_LAYER: {LAYER!r}"
if LAYER == "L0":
    SYSTEM_PROMPT, _TOOLS = _L0_PROMPT, []
elif LAYER == "L0-web":
    SYSTEM_PROMPT, _TOOLS = _L0WEB_PROMPT, [web_search]
elif LAYER == "L1":
    SYSTEM_PROMPT, _TOOLS = _L1_PROMPT, [query_patient_data]
elif LAYER == "L2":
    SYSTEM_PROMPT, _TOOLS = _L2_PROMPT, [knowledge_search, query_patient_data, query_variant_annotation, query_primekg]
elif LAYER == "L3a":
    # Phase B ablation cell: L2 with the GRAPH swapped in for flat KG, NO OLS (graph, -OLS).
    SYSTEM_PROMPT = _L3_PROMPT + ("\n\n(CONFIGURATION NOTE: ontology_lookup is UNAVAILABLE in this run.)")
    _TOOLS = [knowledge_search, get_hub_schema, query_knowledge_graph, query_patient_data, query_variant_annotation]
elif LAYER == "L3b":
    # Phase B ablation cell: L2 (flat KG) + OLS, NO graph (flat, +OLS).
    SYSTEM_PROMPT = _L2_PROMPT + ("\n\nYou also have ontology_lookup for authoritative MONDO/ontology id resolution.")
    _TOOLS = [knowledge_search, query_patient_data, query_variant_annotation, query_primekg, ontology_lookup]
else:
    # L3 (full) and its component-ablation variants (L3_no_graph / L3_no_ols / L3_no_kb).
    # Each ablation drops exactly ONE semantic component from L3 to isolate that component's grounding
    # contribution. The prompt stays science-free; for an ablation we only append a capability note
    # (which tool is unavailable) so the agent doesn't try to call a tool it lacks.
    SYSTEM_PROMPT = _L3_PROMPT
    _TOOLS = [knowledge_search, get_hub_schema, query_knowledge_graph, query_patient_data, query_variant_annotation, ontology_lookup]
    _ABLATE = {
        "L3_no_graph": (query_knowledge_graph,),
        "L3_no_ols": (ontology_lookup,),
        "L3_no_kb": (knowledge_search,),
    }
    if LAYER in _ABLATE:
        _drop = _ABLATE[LAYER]
        _TOOLS = [t for t in _TOOLS if t not in _drop]
        _dropped = ", ".join(getattr(t, "tool_name", getattr(t, "__name__", "?")) for t in _drop)
        SYSTEM_PROMPT = _L3_PROMPT + (
            f"\n\n(CONFIGURATION NOTE: the following capability is UNAVAILABLE in this run: {_dropped}. "
            "Do not attempt to call it; answer using only the tools actually provided to you.)"
        )
logger.info("Agent layer=%s tools=%s", LAYER, [getattr(t, "tool_name", getattr(t, "__name__", "?")) for t in _TOOLS])

# Responsible-AI disclaimer — prepended to EVERY layer's prompt so it always reaches the user
# (Holmes CSR finding #4). Research/demonstration use only; not medical advice. Kept short and
# non-behavioral so it does not alter benchmark answers (it adds no tool/formatting instructions).
_DISCLAIMER = (
    "IMPORTANT — RESEARCH USE ONLY: You are a research and demonstration assistant operating on public, "
    "de-identified data (TCGA and curated open sources). Your output is NOT medical advice and must not be "
    "used for clinical diagnosis, treatment, or patient-care decisions. Do not infer the identity of any "
    "individual. Attribute facts to their source and do not fabricate data or citations.\n\n"
)
SYSTEM_PROMPT = _DISCLAIMER + SYSTEM_PROMPT

# Faithfulness experiment toggle: strip the safety guardrails (statistical-rigor hand-off + citation
# discipline) so we can observe whether the hub's grounding ALONE keeps an agent faithful, vs falling
# back to model memory. Set SEMHUB_STRIP_GUARDS=1. Experimental variant only — never the canonical config.
if os.environ.get("SEMHUB_STRIP_GUARDS") == "1":
    import re as _re
    SYSTEM_PROMPT = _re.sub(r'\n?STATISTICAL RIGOR.*?(?=\n\n|$)', '', SYSTEM_PROMPT, flags=_re.S | _re.I)
    SYSTEM_PROMPT = _re.sub(r'\n?Citation discipline:.*?(?=\n\n|$)', '', SYSTEM_PROMPT, flags=_re.S | _re.I)
    SYSTEM_PROMPT = _re.sub(r'[;,.]? *never invent[^\n.]*\.?', '', SYSTEM_PROMPT, flags=_re.I)
    logger.info("SEMHUB_STRIP_GUARDS=1 -> stripped stat-rigor + citation-discipline guardrails (experiment)")

_STREAMING = os.environ.get("SEMHUB_STREAMING", "1") != "0"  # Llama on Bedrock needs streaming=0 for tool use
_MODEL = BedrockModel(model_id=SUBJECT_MODEL_ID, region_name=REGION, streaming=_STREAMING, temperature=float(os.environ.get("SEMHUB_TEMP", "0.0")))
_SESSIONS: dict[str, Agent] = {}


@app.entrypoint
async def invoke(payload, context):
    prompt = payload.get("prompt", "")
    sid = getattr(context, "session_id", None)
    logger.info("prompt (session=%s): %s", sid, prompt[:80])
    if sid and sid in _SESSIONS:
        agent = _SESSIONS[sid]
    else:
        agent = Agent(model=_MODEL, tools=_TOOLS, system_prompt=SYSTEM_PROMPT)
        if sid:
            _SESSIONS[sid] = agent
    parts = []
    async for event in agent.stream_async(prompt):
        if "data" in event:
            parts.append(str(event["data"]))
    answer = re.sub(r"<thinking>.*?</thinking>", "", "".join(parts), flags=re.DOTALL).strip()
    # Token usage for benchmarking (best-effort; never fail the response if metrics shape differs).
    usage = {}
    try:
        au = getattr(getattr(agent, "event_loop_metrics", None), "accumulated_usage", None)
        if au:
            usage = {"input_tokens": au.get("inputTokens"),
                     "output_tokens": au.get("outputTokens"),
                     "total_tokens": au.get("totalTokens")}
    except Exception as _e:  # noqa: BLE001
        logger.warning("token-usage capture failed: %s", _e)
    return {"answer": answer, "usage": usage}


if __name__ == "__main__":
    app.run()
