# ADR 0002 — One env-gated agent spanning L0–L3 for apples-to-apples benchmarking

**Status:** Accepted

## Context

The accelerator's central claim is that *organizing the same data as a semantic hub* makes an agent
measurably more correct and reproducible. Proving that requires comparing tiers that differ **only** in
data organization — not in model, temperature, or prompt scaffolding — otherwise the measured lift is
confounded. The tiers are: L0 (bare LLM, no tools), L1 (lake only), L2 (all data, flat organization),
L3 (full semantic hub: graph + ontology + RODA + KB), plus ablations (L3_no_graph / L3_no_ols /
L3_no_kb).

## Decision

Implement **a single agent file** (`agentcore/semantic_hub_agent.py`) whose tier is selected by one
environment variable (`SEMHUB_LAYER`). Layer selection is the only switch that changes the tool list
and system prompt; model (Claude Sonnet 4.5), temperature (0.0), and the attempt-and-attribute
provenance discipline are identical across tiers. Each tier deploys as its own AgentCore runtime via
the same `deploy.py --layer <L>`.

## Consequences

- **Positive:** the benchmark is a controlled experiment — the only independent variable is data
  organization, so the correctness/reproducibility deltas are attributable to the semantic layer.
- **Positive:** one codebase to maintain; ablations are first-class, not forks.
- **Negative:** deploying the full ladder creates multiple runtimes + IAM roles that must each be
  torn down (handled by `agentcore/cleanup.py --all`).
- **Negative:** the single-file agent carries all tiers' tool definitions and prompt branches, which
  is more complex than a single-purpose agent would be.

## Source rationale

`docs/benchmark-report.md` (tier ladder + methodology); `agentcore/README.md` (Layer architecture
table — same model/temp across layers).
