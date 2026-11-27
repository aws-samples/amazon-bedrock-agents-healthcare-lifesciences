"""Read-only guards for every hub query path (defense-in-depth on top of least-privilege IAM).

Used by the data MCP server (mcp_server.py), the deployed agent's tools (agentcore/semantic_hub_agent.py)
and the evaluation harness tools (evaluation/hub_tools.py). The hub is read-only by design. IAM already
withholds write actions (no neptune-graph WriteDataViaQuery, no Athena/Glue writes), but these in-process
guards reject mutating requests BEFORE they reach AWS — clearer errors and a second layer. They have no
on/off switch (SEMHUB_STRIP_GUARDS only edits prompt text). Pure functions, no deps → unit-testable.
"""
from __future__ import annotations

import re

# openCypher write clauses (word-boundary, case-insensitive). Reads are MATCH/RETURN/WITH/UNWIND/CALL.
_CYPHER_MUTATION = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|LOAD\s+CSV)\b", re.IGNORECASE)
# Neptune Analytics write procedures: bulk load (`CALL neptune.load(...)`) and the algorithm
# `.mutate` variants that write results back into the graph. Read-only `CALL neptune.algo.<x>(...)`
# stays allowed.
_CYPHER_WRITE_PROC = re.compile(
    r"\bneptune\s*\.\s*load\b|\.\s*mutate\s*\(", re.IGNORECASE)

# SQL statements allowed (read-only). Everything else is rejected.
_SQL_READ_START = re.compile(r"^(SELECT|WITH|SHOW|DESCRIBE|DESC|EXPLAIN)\b", re.IGNORECASE)
_SQL_WRITE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|MERGE|MSCK|GRANT|REVOKE|TRUNCATE|UNLOAD|OPTIMIZE|VACUUM)\b",
    re.IGNORECASE)


class ReadOnlyViolation(ValueError):
    """Raised when a query would mutate data or isn't an allowed read statement."""


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)          # line comments
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)  # block comments
    return sql.strip()


def reject_mutations(cypher_query: str) -> str:
    """Return the query if it is a read-only openCypher query; else raise ReadOnlyViolation."""
    if not cypher_query or not cypher_query.strip():
        raise ReadOnlyViolation("empty query")
    m = _CYPHER_MUTATION.search(cypher_query)
    if m:
        raise ReadOnlyViolation(
            f"write clause '{m.group(0).upper()}' not allowed — this endpoint is read-only")
    m = _CYPHER_WRITE_PROC.search(cypher_query)
    if m:
        raise ReadOnlyViolation(
            f"write procedure '{m.group(0)}' not allowed — this endpoint is read-only")
    return cypher_query


def require_select(sql_query: str) -> str:
    """Return the query if it is a single read-only SQL statement; else raise ReadOnlyViolation."""
    if not sql_query or not sql_query.strip():
        raise ReadOnlyViolation("empty query")
    cleaned = _strip_sql_comments(sql_query)
    # Reject stacked statements (a trailing ';' is fine; a second non-empty statement is not).
    parts = [p for p in cleaned.split(";") if p.strip()]
    if len(parts) > 1:
        raise ReadOnlyViolation("multiple SQL statements are not allowed")
    stmt = parts[0] if parts else ""
    if not _SQL_READ_START.match(stmt):
        raise ReadOnlyViolation("only read-only queries are allowed (must start with SELECT/WITH/SHOW/DESCRIBE/EXPLAIN)")
    if _SQL_WRITE.search(stmt):
        raise ReadOnlyViolation("write/DDL keyword detected — this endpoint is read-only")
    return sql_query
