"""Shared hub query executors (read-only).

Extracted verbatim from `agentcore/semantic_hub_agent.py` so the agent AND the remote MCP server run
ONE implementation of Neptune/Athena access (no drift). Behavior is identical to the agent's original
inline code. Read-only guards (reject mutations / non-SELECT) live in the MCP server layer, not here.

Config via env (matches the agent + deploy.py injection): SEMHUB_REGION, SEMHUB_GRAPH_ID,
SEMHUB_ATHENA_WG, SEMHUB_ATHENA_OUTPUT. Clients are created lazily; both functions accept an optional
`client=` for unit testing.
"""
from __future__ import annotations

import json
import os
import time

import boto3

REGION = os.environ.get("SEMHUB_REGION", "us-west-2")
GRAPH_ID = os.environ.get("SEMHUB_GRAPH_ID", "")
ATHENA_WORKGROUP = os.environ.get("SEMHUB_ATHENA_WG", "primary")
ATHENA_OUTPUT = os.environ.get("SEMHUB_ATHENA_OUTPUT", "")

_neptune = None
_athena = None


def _nep():
    global _neptune
    if _neptune is None:
        _neptune = boto3.client("neptune-graph", region_name=REGION)
    return _neptune


def _ath():
    global _athena
    if _athena is None:
        _athena = boto3.client("athena", region_name=REGION)
    return _athena


def run_opencypher(cypher_query: str, graph_id: str | None = None, client=None) -> str:
    """Execute a read openCypher query against Neptune Analytics; return results JSON (truncated at 8k)."""
    neptune = client or _nep()
    r = neptune.execute_query(graphIdentifier=(graph_id or GRAPH_ID), queryString=cypher_query,
                              language="OPEN_CYPHER")
    results = json.loads(r["payload"].read().decode()).get("results", [])
    text = json.dumps(results, indent=2, default=str)
    return text[:8000] + "\n... (truncated)" if len(text) > 8000 else text


def run_athena_sql(sql_query: str, database: str, workgroup: str | None = None,
                   output: str | None = None, client=None) -> str:
    """Run an Athena query in `database`; return columns+rows as JSON (first 200 rows). Shared by the
    lake tools (patient data / RODA variant annotation / flat PrimeKG)."""
    athena = client or _ath()
    q = athena.start_query_execution(
        QueryString=sql_query,
        QueryExecutionContext={"Database": database},
        WorkGroup=workgroup or ATHENA_WORKGROUP,
        ResultConfiguration={"OutputLocation": output or ATHENA_OUTPUT})
    qid = q["QueryExecutionId"]
    while True:
        status = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        st = status["State"]
        if st in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)  # nosemgrep  (intentional sleep: async-AWS poll)
    if st != "SUCCEEDED":
        return f"Query {st}: {status.get('StateChangeReason', '')}"[:600]
    rows = []
    for page in athena.get_paginator("get_query_results").paginate(QueryExecutionId=qid):
        for row in page["ResultSet"]["Rows"]:
            rows.append([c.get("VarCharValue", "") for c in row["Data"]])
    if not rows:
        return "No results."
    return json.dumps({"columns": rows[0], "rows": rows[1:201]}, indent=2)
