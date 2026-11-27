# ADR 0004 — In-process boto3 tools for the benchmark agent; a separate remote MCP server for other clients

**Status:** Accepted (both halves are built and deployed)

## Context

The hub's Neptune/Athena query tools could be exposed to clients in two ways: (a) as in-process Strands
`@tool` functions that call boto3 directly inside the deployed benchmark agent, or (b) as a **remote MCP
server** on AgentCore Runtime that any MCP-compatible client (Amazon Quick, Claude Code, Kiro, a custom
agent) calls over HTTPS+JWT without local AWS credentials. These are not mutually exclusive — the hub
ships both, as two consumers of one shared query core.

## Decision

- **(a) In-process boto3 tools** for the benchmark agent (`agentcore/semantic_hub_agent.py`), calling
  `hub_core/queries.py` directly. Kept in-process deliberately for ablation control (L0–L3, L3a/b,
  L3_no_*) — the benchmark needs to add/remove exactly one tool per cell without touching a network
  boundary.
- **(b) A separate remote MCP server, `oncology-hub-data`**, deployed on AgentCore Runtime
  (`serverProtocol=MCP`), exposing `get_hub_schema` / `query_knowledge_graph` / `query_patient_data` /
  `query_variant_annotation` over HTTPS, authenticated via a CUSTOM_JWT authorizer that reuses the
  Ontology Lookup Service's Cognito pool (no new Cognito stack). Read-only in-process guards
  (`_reject_mutations` / `_require_select`) plus least-privilege IAM. This server imports the **same**
  `hub_core/` as the benchmark agent — one implementation, two consumers, no drift (see ADR 0003).
  `ontology_lookup` and `knowledge_search` are further separate MCP servers (OLS; Bedrock KB
  retrieval) — not part of this server.

Originally documented as a design (`docs/remote-mcp-server-design.md`, then `Status: PLAN`) with the
intent to build it later; it has since been built and deployed. The design doc is kept as the record of
*why* it's shaped this way (Cognito reuse, read-only guards, the `hub_core` refactor) and now carries a
status-update note pointing at the shipped location.

## Consequences

- **Positive:** the benchmark stays simple (no network hop, clean ablation story) while non-AWS-SDK
  clients get a governed, credential-free HTTPS path to the exact same data — without duplicating query
  logic (both consumers import `hub_core/`).
- **Positive:** read-only guards + least-privilege IAM bound the blast radius of a public(ish),
  JWT-gated endpoint.
- **Operational cost:** the remote server has its own deploy/teardown lifecycle (a second
  `deploy.py`/`cleanup.py`, a dependency on the OLS Cognito stack being deployed first) — this is real,
  ongoing surface, not a one-time cost.
- **Guard against drift:** `docs/bring-your-own-data.md` must describe BYOD in terms of the *actual*
  shipped surfaces (the in-process agent tools for the benchmark, `oncology-hub-data` for Quick/other
  clients) rather than a generic "AWS Labs MCP servers" framing that doesn't name what's really deployed.

## Source rationale

`docs/remote-mcp-server-design.md` (design + status update); `mcp-servers/agentcore-runtime/
oncology-hub-data/README.md` and `runtime_config.json` (shipped artifact, live `agent_arn`); ADR 0003
(schema-discovery-first generic tools — the shared contract both consumers rely on).
