---
name: grounding-faithfulness-eval
description: >-
  Use AFTER an agent produces an answer that cites sources with inline bracket tags (e.g. [Graph],
  [Lake:table], [OLS], [KB PMID:...], [RODA:table], [Model knowledge], [Recalled: src]) to compute two
  real-time, ground-truth-free trust metrics: grounding_rate (share of the answer backed by tool
  retrievals vs model memory) and provenance-faithfulness (attribution honesty — flags "fabricated
  grounding", i.e. claiming a tool/source the agent's connected tools cannot produce). Domain-agnostic
  and reusable across any tool-using agent that emits provenance tags. Not for correctness (needs
  ground truth) or reproducibility (needs multiple runs).
---

# Grounding & Faithfulness Evaluation

Compute two **deterministic, single-response** trust metrics from an answer's inline provenance tags —
no ground truth, no extra model call. Definitions match the Oncology Semantic Hub benchmark report
(§12/§12b): the same scorer runs here (live) and in the batch benchmark, so numbers are consistent.

## When to use
Right after the agent has composed a final answer in which **every fact is tagged by its source**.
Use this to surface trust to the user immediately. Do **not** use it for correctness or reproducibility.

## Metrics
- **grounding_rate** — fraction of tags that are tool-retrieved (`[Graph]`/`[Lake]`/`[OLS]`/`[KB]`/`[RODA]`/`[Web]`/`[Compute]`)
  vs `[Model knowledge]`/`[Recalled]`. Low is **not** unfaithful — honest use of model memory is fine.
- **provenance_faithfulness** — `1 − fabricated/total`, where *fabricated* = a tag the agent's connected-tool
  **inventory** cannot produce (e.g. claiming `[Graph]` when no graph tool is connected). `1.0` = honest attribution.
- `n_tags` and `fabricated` (list) are also returned. An **untagged** answer returns `null` metrics with
  `note: "no provenance tags (unauditable)"` — that is not a zero score.

## Prerequisites
- `python3` (3.9+) — the script is stdlib-only, no dependencies. `uv` is optional (`uv run` also works).

## Available scripts
- **`scripts/score_provenance.py`** — reads the answer from **stdin** (or `--answer-file`), prints JSON
  metrics to stdout. `--inventory` selects the connected-tool set. Run `--help` for details.

## Workflow
1. Make sure the answer tags every fact inline, one of: `[Graph]`, `[Lake:<table>]`, `[OLS]`,
   `[KB PMID:...]`, `[RODA:<table>]`, `[Web:<url>]`, `[Model knowledge]`, `[Recalled: <src>]`.
2. Score it (pass `--inventory` matching the agent's actually-connected tools):
   ```bash
   printf '%s' "$ANSWER" | python3 scripts/score_provenance.py --inventory quick
   ```
3. Report `grounding_rate` and `provenance_faithfulness` to the user. If `fabricated` is non-empty,
   warn that the answer claimed a source it could not have produced.

## Inventory options (`--inventory`)
`quick` (default — Neptune+Athena data MCP server + OLS MCP: graph/lake/roda/ols/kb), `L3`, `L2`, `L1`,
`L0`, `L0-web`. Pick the one matching the tools connected to the agent.

## Notes
- **Depends on the agent emitting tags.** Pair this with a domain/workflow skill (e.g.
  `oncology-semantic-hub-analysis`) that instructs inline tagging with a tool→tag map.
- Output is small JSON (safe for agent context). Data goes to stdout; warnings to stderr.
