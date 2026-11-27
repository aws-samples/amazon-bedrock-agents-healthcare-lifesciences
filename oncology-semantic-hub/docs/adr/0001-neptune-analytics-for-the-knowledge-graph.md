# ADR 0001 — Neptune Analytics (not Neptune Database) for the knowledge graph

**Status:** Accepted

## Context

The hub's context layer is a ~174K-node / ~4M-edge knowledge graph (PrimeKG backbone + TCGA
case/sample nodes + CIViC/ClinVar/COSMIC/MONDO enrichments). The hub needs two things from it: (1)
read-only openCypher traversal at agent-query time, and (2) graph-analytics (centrality, community,
PageRank, path-finding) for target/biomarker discovery (`scripts/12_graph_algorithms.py`). The graph
is rebuilt from source by a batch pipeline, not mutated transactionally by an application.

Amazon Neptune offers two engines: Neptune Database (provisioned instances, OLTP-style transactional
graph) and Neptune Analytics (an in-memory analytics engine with built-in graph algorithms and vector
support, loaded from S3).

## Decision

Use **Neptune Analytics**. The graph is loaded by bulk-import from S3 CSVs
(`scripts/08_neptune_bulk_import.py`) and queried read-only via `neptune-graph:ReadDataViaQuery`;
schema introspection uses `GetGraphSummary`.

## Consequences

- **Positive:** built-in algorithms serve the discovery use case without a separate analytics stack;
  bulk-load-from-S3 matches the rebuild-from-source pipeline; m-NCU capacity is the single cost knob.
- **Positive:** read-only access pattern aligns with least-privilege IAM (no graph-write actions
  granted to the agent or MCP roles).
- **Negative / cost:** m-NCU capacity bills continuously whether or not the graph is queried — the
  dominant steady-state cost (~$65/mo at 32 m-NCU in the reference deployment) and the first thing to
  destroy at teardown (see `docs/TEARDOWN.md`).
- **Negative:** not suited to transactional per-row writes; the onboarding/enrichment model is
  additive batch extension, not live mutation.

## Source rationale

`docs/semantic-hub-oncology-lens.md` (Context lane: Neptune Analytics for target/biomarker discovery);
`scripts/README.md` and `scripts/12_graph_algorithms.py`.
