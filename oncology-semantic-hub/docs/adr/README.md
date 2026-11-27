# Architecture Decision Records

Each ADR records **one** significant decision: the context, the choice, and the consequences — so a
future engineer can tell an intentional decision from an accident. These are promoted from the design
and status docs where the reasoning was originally worked out (cited in each record).

Format: lightweight [MADR](https://adr.github.io/madr/)-style. Status is one of
`Accepted` / `Superseded` / `Proposed`.

| ADR | Title | Status | Source rationale |
|---|---|---|---|
| [0001](0001-neptune-analytics-for-the-knowledge-graph.md) | Neptune Analytics (not Neptune DB) for the knowledge graph | Accepted | semantic-hub-oncology-lens.md; scripts/ |
| [0002](0002-layered-l0-l3-agent-for-benchmarking.md) | One env-gated agent spanning L0–L3 for apples-to-apples benchmarking | Accepted | benchmark-report.md; agentcore/README.md |
| [0003](0003-schema-discovery-first-generic-tools.md) | Schema-discovery-first generic tools (not per-dataset tools) | Accepted | remote-mcp-server-design.md §5/§13 |
| [0004](0004-in-process-tools-now-remote-mcp-later.md) | In-process boto3 tools now; remote MCP server deferred | Accepted | remote-mcp-server-design.md (PLAN) |
| [0005](0005-env-driven-config-no-hardcoded-account-region.md) | Env-driven config; never hardcode account/region | Accepted | scripts/_config.py; backlog.md |

## Why these five

The hub's non-obvious shape comes from these decisions. Everything else (which datasets, which
enrichments) is documented in the data-pipeline and dataset docs; these records capture the
*architectural* "why" that is otherwise scattered across design docs.
