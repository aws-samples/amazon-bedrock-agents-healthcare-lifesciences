# Latency / Cost scratch analysis — Haiku 4.5 (NOT for the report)

**Status: SCRATCH / for later analysis only.** Owner decision (2026-08-18): do NOT publish these
latency/token numbers — L2 and L3 are too similar on the correctness-conditioned comparison to draw a
conclusion. Kept here for future reference; revisit if we expand the dataset or get a cross-model set.

- Source: `output/v2_benchmark_results_haiku.json` (run_id 352b1781b387, 2026-08-17T20:50:01.880253+00:00)
- Model (all layers): us.anthropic.claude-haiku-4-5-20251001-v1:0
- Latency = client-side wall-clock per invoke, captured at workers=4 (contention) — directional, not an SLA.
- Tokens = agent accumulated Bedrock usage (input+output). Medians across the 5-run per-question means.

## Methodology note (the key point)
Comparing latency/cost to reach a **wrong** answer is meaningless (L2 is often "fast because it's wrong").
The fair comparison is the **both-correct subset**: questions where L2 AND L3 both score >= 0.8.

Correctness split (of 84): both-correct = 41; excluded = {'L3-only correct (hub lift)': 11, 'neither correct': 27, 'L2-only correct': 2}.
The "L3-only correct (hub lift)" bucket is where L3 wins on correctness — no latency comparison possible there.

## Table A — BOTH-CORRECT subset (fair comparison)
| category | n | L2 lat ms | L3 lat ms | L2 tok | L3 tok |
|---|---|---|---|---|---|
| actionability | 5 | 12099 | 15856 | 7587 | 10506 |
| evidence | 1 | 21456 | 25706 | 23278 | 33063 |
| graph_1hop | 9 | 11518 | 9286 | 6025 | 6510 |
| graph_multihop | 4 | 29782 | 36660 | 38896 | 54734 |
| lake | 17 | 10289 | 10277 | 5747 | 6583 |
| multi_source | 1 | 20847 | 16839 | 15552 | 12894 |
| negative | 3 | 20713 | 18672 | 17261 | 18263 |
| reconciliation | 1 | 10524 | 20478 | 7132 | 8324 |
| **OVERALL** | 41 | 11404 | 10668 | 5939 | 6590 |

## Table B — ALL questions (reference; confounded by fast-but-wrong L2)
| category | n | L2 lat ms | L3 lat ms | L2 tok | L3 tok |
|---|---|---|---|---|---|
| actionability | 7 | 23817 | 18761 | 31817 | 22666 |
| evidence | 2 | 23048 | 24064 | 24964 | 28174 |
| graph_1hop | 11 | 11495 | 9286 | 6025 | 6510 |
| graph_multihop | 14 | 31932 | 37829 | 50111 | 55646 |
| lake | 18 | 10340 | 10330 | 5746 | 6583 |
| multi_source | 8 | 29741 | 45366 | 62985 | 107108 |
| negative | 6 | 22232 | 18131 | 28640 | 18174 |
| ontology | 6 | 17334 | 15922 | 14126 | 18563 |
| reconciliation | 9 | 10703 | 26413 | 7132 | 27088 |
| **OVERALL** | 81 | 13028 | 16839 | 7587 | 17104 |

## Takeaways (why not reported)
- Overall both-correct: L2 vs L3 latency/tokens are ~similar (L3 marginally faster, ~10% more tokens) — inconclusive.
- Only `graph_1hop` (n=9, L3 faster) and `lake` (n=17, tied) have enough both-correct samples to trust.
- Hard categories (reconciliation/multi_source/graph_multihop) have tiny both-correct n because L2 is wrong there,
  so per-category latency is not interpretable.
- To get a real cost/latency story: (a) expand the dataset, and/or (b) run Sonnet with latency+token capture
  for a cross-model both-correct comparison.
