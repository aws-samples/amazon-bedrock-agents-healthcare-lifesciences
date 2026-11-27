# ADR 0003 — Schema-discovery-first generic tools (not per-dataset tools)

**Status:** Accepted

## Context

The agent reaches the data plane through a small set of tools. A naive design gives each dataset its
own tool (e.g. `query_civic`, `query_tcga_mutations`), which couples the agent to the exact set of
datasets: adding a dataset means editing agent code, and `get_hub_schema` returning a hardcoded
description string means a newly added table is invisible to the agent until that string is edited.
This directly undercuts the bring-your-own-data story, where a customer points the agent at *their*
catalog.

## Decision

Expose **generic, parameterized executors**, not per-dataset tools:
`query_knowledge_graph(cypher)`, `query_patient_data(sql)`, `query_variant_annotation(sql)` — each a
read-only query runner scoped to a database/graph. Pair them with a **live** `get_hub_schema` that
introspects the catalog at call time: Glue `GetDatabases`/`GetTables` over the Athena databases plus
Neptune `GetGraphSummary`, with curated semantic hints (MONDO anchoring, partition columns) layered on
as a static preamble (`hub_core/schema.py`). A newly registered table self-surfaces to the agent with
no code change.

## Consequences

- **Positive:** adding or swapping datasets is a data/catalog operation, not an agent-code change —
  the "point the same tools at your own resources" BYOD claim holds in code.
- **Positive:** one shared implementation (`hub_core/queries.py` + `hub_core/schema.py`) is reused by
  the agent today and by a future remote MCP server (see ADR 0004), avoiding drift.
- **Negative:** generic SQL/Cypher executors require read-only guards and least-privilege IAM to stay
  safe (there is no per-tool allowlist of what can be queried); the agent must compose correct queries
  from the discovered schema rather than relying on bespoke tool semantics.
- **Trade-off:** `SEMHUB_SCHEMA_DBS` controls which databases are introspected (e.g. the L2 flat-
  PrimeKG DB is excluded from L3's schema) — a config surface a BYOD user must know about.

## Source rationale

`docs/remote-mcp-server-design.md` §5 ("Refactor first — one shared query core") and §13.4
(`get_hub_schema` shipped as live introspection, static fallback retained).
