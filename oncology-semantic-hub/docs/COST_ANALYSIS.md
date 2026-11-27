# Cost Analysis — Oncology Semantic Hub

How the deployed hub behaves economically from a pilot to beyond production scale, so a customer can
size it and know where the current architecture stops being optimal. Pricing is **us-west-2, on-demand,
2025 public rates**; confirm against the [Bedrock](https://aws.amazon.com/bedrock/pricing/) and
service pricing pages before quoting a customer — rates change and this doc is a snapshot.

## Assumptions

| Scale | Definition | Research queries / month | Tokens per query (in / out) |
|---|---|---|---|
| **Pilot** | one research team | ~2,000 | ~6,000 in / ~1,500 out |
| **Production** | one cancer center / department | ~100,000 | ~6,000 in / ~1,500 out |
| **10× Production** | multi-institution | ~1,000,000 | ~6,000 in / ~1,500 out |

Token assumptions are deliberately higher-input than a chatbot: an L3 answer is **multi-hop** — schema
discovery + several Neptune/Athena tool calls + KB passages are fed back into the model, so input
dominates. Measure your own `NTags`/token usage from the benchmark (`run_v2_benchmark.py` captures
`usage`) and re-run the math; the per-token line is the only one that scales steeply.

**Fixed (always-on) vs variable:** Neptune Analytics (m-NCU) and the Bedrock Knowledge Base (S3 Vectors
storage) bill **continuously regardless of query volume**. Everything else is **per-use** and scales
with queries. This split is the key to the cost story.

## Per-service monthly cost

| Service | Cost driver | Pilot | Production | 10× Production |
|---|---|---|---|---|
| **Bedrock — Claude Sonnet 4.5** | per token ($3/1M in, $15/1M out) | ~$81 | ~$4,050 | ~$40,500 |
| **Neptune Analytics** | per m-NCU-hour (fixed) | ~$65 | ~$65 | ~$130† |
| **Bedrock Knowledge Base (S3 Vectors + Titan v2 embed)** | vector storage (fixed) + per-query embed | ~$5 | ~$15 | ~$80 |
| **AgentCore Runtime** | per request + duration | ~$1 | ~$50 | ~$500 |
| **Athena** | per TB scanned (Parquet + partitioned) | ~$1 | ~$30 | ~$300 |
| **S3 (lake + results + corpus)** | per GB stored + requests | ~$2 | ~$5 | ~$30 |
| **CloudWatch (metrics + logs)** | per metric + per GB ingested | ~$2 | ~$20 | ~$150 |
| **Glue (catalog + crawler)** | per object + crawler-hour | ~$1 | ~$1 | ~$2 |
| **Total (rounded)** | | **~$158/mo** | **~$4,236/mo** | **~$41,700/mo** |

† Neptune Analytics m-NCU is sized to **graph size**, not query volume (the graph is ~174K nodes / ~4M
edges at any scale), so it stays flat until a larger/BYOD graph needs more capacity — modeled as a step
to 64 m-NCU at 10×. The reference deployment runs ~32 m-NCU ≈ $65/mo.

**Bedrock token cost example (production):** 100,000 queries × (6,000 × $3/1M + 1,500 × $15/1M) =
100,000 × ($0.018 + $0.0225) = 100,000 × $0.0405 ≈ **$4,050/mo**. This is ~96% of production spend and
is where any optimization effort belongs.

## Where the cost goes, by scale

- **Pilot (~$158/mo):** dominated by the two **fixed** costs — Neptune Analytics (~$65) + the always-on
  overhead. The agent's token cost (~$81) is comparable to the fixed infra. At this scale the hub is
  "mostly rent" — turning it off between pilots (teardown) is the biggest lever.
- **Production (~$4.2K/mo):** the crossover has happened — **Bedrock tokens are ~96% of spend** and the
  fixed infra is a rounding error. Nothing about the graph/lake scales here; the model does.
- **10× (~$42K/mo):** still token-bound. Fixed infra barely moves; the bill is essentially linear in
  query volume via the LLM.

## Architecture trade-offs at scale (where the current design stops being optimal)

1. **Token cost is the only steep line — optimize there first.** At production+ scale, cutting input
   tokens beats any infra change. Highest-leverage: (a) **prompt caching** on the stable system prompt +
   schema preamble (the `get_hub_schema` output is large and repeats every call); (b) tighter tool-result
   truncation before feeding Neptune/Athena rows back to the model; (c) a cheaper model (Haiku) for L0/L1
   tiers and simple 1-hop questions — the benchmark already carries `*_haiku` configs to quantify the
   quality trade.
2. **Fixed vs on-demand is a pilot-only question.** Neptune Analytics m-NCU and KB vector storage are
   always-on; at **pilot** they dominate, so the economically correct move between pilots is to **tear
   down** (see `docs/TEARDOWN.md`) rather than idle. At production the fixed cost is noise — leave it up.
3. **Athena stays cheap only while the lake is Parquet + partitioned.** The ETL already writes
   partitioned Parquet; a BYOD customer who lands raw CSV or an unpartitioned lake can turn the ~$30/mo
   Athena line into something much larger (per-TB-scanned). Keep the Parquet/partition discipline.
4. **AgentCore vs self-hosting the model** is *not* worth it even at 10×. The ~$42K/mo is Bedrock
   per-token inference; self-hosting Sonnet-class inference at ~1M queries/mo is almost certainly more
   expensive and far more operationally complex than the managed per-token API. The LLM-behind-an-API
   choice remains correct across all three scales modeled here — the inflection where self-hosting wins
   is well beyond 10× and only for sustained, saturated throughput.
5. **PHI/BYOD changes the cost basis, not just the security posture.** Real patient data pulls in the
   hardening in `docs/bring-your-own-data.md` (per-user identity, VPC networking, KMS CMKs, richer
   logging) — each adds cost not modeled here (NAT/endpoints, KMS, higher CloudWatch). Budget it
   separately when leaving the public-TCGA demo configuration.

## How to re-estimate for your deployment

1. Run `python agentcore/run_v2_benchmark.py` and read the captured `usage` for your real tokens/query.
2. Replace the token assumptions above; the Bedrock line = `queries × (in×$3/1M + out×$15/1M)`.
3. Check your Neptune m-NCU setting (`aws neptune-graph get-graph`) for the fixed line.
4. Everything else is small and scales with query volume — the two numbers that matter are **tokens/query**
   and **queries/month**.
