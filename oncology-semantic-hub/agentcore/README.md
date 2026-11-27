# Oncology Semantic Hub Agent (Accelerator 1)

A working, deployable oncology research agent on Amazon Bedrock AgentCore — with a bring-your-own-data
pathway for customers to extend with their own cohort and datasets.

## What's here

| File | Purpose |
|---|---|
| `semantic_hub_agent.py` | THE agent — single file, env-gated (L0/L1/L2/L3/ablations), Strands framework |
| `deploy.py` | Package + deploy to AgentCore Runtime (any layer) |
| `run_agentcore_eval.py` | Run native AgentCore evaluation (Builtin.Correctness + Faithfulness) |
| `run_v2_benchmark.py` | Run custom benchmark (F1 + 5× reproducibility + self-agreement) |
| `chat_ui.py` | Streamlit compare-mode UI (side-by-side L0/L2/L3) — shows live provenance metrics per answer |
| `realtime_metrics.py` | Real-time provenance-faithfulness + grounding_rate (single response, no ground truth) + CloudWatch/EMF emit |
| `kb/build_corpus.py` | Build the literature Knowledge Base corpus |
| `agent_config.example.json` | Template config (deploy.py writes the real one) |

## Quick start

### Prerequisites
- Data pipeline completed (`scripts/01_*` – `scripts/16_*` + `scripts/roda/`)
- Neptune Analytics graph loaded (PrimeKG + TCGA case nodes)
- Athena tables created (tcga_mutations, tcga_expression, source_cbioportal)
- OLS MCP server deployed (see `agents_catalog/35-Terminology-agent/`)
- Bedrock Knowledge Base created (`kb/build_corpus.py` + console/API)

### Deploy

```bash
# Full semantic hub (L3)
python deploy.py --layer L3

# Flat-data baseline (L2) — same data, no graph/OLS
python deploy.py --layer L2

# Bare LLM floor (L0) — no tools
python deploy.py --layer L0

# Ablations
python deploy.py --layer L3a  # graph, -OLS
python deploy.py --layer L3b  # flat, +OLS
```

Each deploy writes `agent_config[_<layer>].json` with the runtime ARN.

### Run the demo app

```bash
streamlit run chat_ui.py
# Opens http://localhost:8501 — Compare mode with L0/L2/L3 toggles
```

### Run the benchmark

```bash
# Native AgentCore evaluation
python run_agentcore_eval.py

# Custom benchmark (5× reproducibility)
python run_v2_benchmark.py

# ...and publish per-layer aggregate metrics to CloudWatch (batch-job timestamp)
python run_v2_benchmark.py --emit-metrics

# Results → output/
```

## Real-time provenance metrics (live groundedness)

Two of the benchmark's metrics can be computed **at response time** — from a single answer, with no
golden ground truth and no extra model call — so they can be surfaced to a user immediately:

- **provenance-faithfulness** — layer-aware attribution honesty. `1.0` = every source tag the answer
  emits is one this layer's tools can actually produce; `<1.0` = *fabricated grounding* (e.g. an L2
  answer claiming `[Graph]`, a tool it does not have).
- **grounding_rate** — fraction of tags that are tool-retrieved vs `[Model knowledge]`/`[Recalled]`.

(Correctness needs verified ground truth; reproducibility needs N runs — both stay batch-only.)

`realtime_metrics.py` reuses the canonical scorer (`evaluation/provenance_faithfulness.py`), so
real-time numbers match the batch report by construction.

```python
from realtime_metrics import compute_realtime, emit_cloudwatch
m = compute_realtime(answer, "L3")     # {provenance_faithfulness, grounding_rate, n_tags, fabricated}
emit_cloudwatch(m, layer="L3", mode="realtime", timestamp=invoked_at, region="us-west-2")
```

**In the demo UI:** the sidebar has **"Show provenance metrics"** (on by default — badges under each
answer, in both Chat and Compare modes) and **"Emit to CloudWatch (real-time)"** (off by default).
The clearest L2-vs-L3 grounding contrast is the **multi-hop** example question (EGFR pathways →
co-mutated GBM genes → druggable): L3 grounds ~100% in tools while L2 backfills a few claims from
model knowledge. Simple 1-hop questions are usually at parity.

**Observability (AgentCore observability = CloudWatch).** Both paths publish the same metric
definitions, distinguished by a `Mode` dimension and by timestamp semantics:

| Path | How | Timestamp | `Mode` |
|---|---|---|---|
| Real-time | UI toggle / `emit_cloudwatch(...)` (or `emit_emf(...)` in-runtime) | agent-invocation time | `realtime` |
| Batch | `run_v2_benchmark.py --emit-metrics` | batch-job time | `batch` |

- **Namespace:** `OncologySemanticHub/Metrics`. **Dimensions:** `Layer`, `Mode` (+ `Model` when the
  agent config carries `subject_model`). **Metrics:** `ProvenanceFaithfulness`, `GroundingRate`,
  `NTags`, `FabricatedGroundingCount` (+ `Correctness` for batch).
- **Two backends:** `emit_cloudwatch` (`PutMetricData`; needs `cloudwatch:PutMetricData`) and
  `emit_emf`/`emf_dict` (EMF log line for in-runtime — no extra IAM; CloudWatch auto-extracts).
  Emission is best-effort and never breaks the agent/UI.
- Unauditable (untagged) answers report `None` and are skipped — no false `0.0` on dashboards.

**Dependency / Quick Desktop note (deferred):** real-time metrics require the agent to emit inline
provenance tags (`[Lake]`/`[Graph]`/`[OLS]`/`[KB]`/`[Model knowledge]`). The deployed L0–L3 agents
already do. For **Amazon Quick Desktop** we will supply a Quick skill that instructs the Quick agent
to emit the same tags, so this feature carries over — tracked as backlog #23.

## Layer architecture

| Layer | Tools | What it tests |
|---|---|---|
| **L0** | None | Pure LLM parametric knowledge floor |
| **L1** | `query_patient_data` (Athena) | Lake-only baseline |
| **L2** | lake + KB + `query_primekg` (flat SQL) + `query_variant_annotation` | All data, flat organization |
| **L3** | lake + KB + `query_knowledge_graph` (Neptune) + `ontology_lookup` (OLS) + RODA | Full semantic hub |

All layers: same model (Claude Sonnet 4.5), same temperature (0.0), attempt-and-attribute provenance.

## Bring your own data

1. **Swap the patient cohort:** replace TCGA with your VCF/MAF/clinical tables in Athena. Update
   `SEMHUB_ATHENA_DB` env var.
2. **Swap/extend the knowledge graph:** load your enterprise KG into Neptune (or extend PrimeKG with
   domain-specific nodes). Update `SEMHUB_GRAPH_ID` env var.
3. **Add RODA datasets:** use `scripts/roda/` pipeline to onboard additional open datasets.
4. **Update the Knowledge Base:** rebuild the corpus with your literature (`kb/build_corpus.py`).
5. **Deploy + benchmark:** same `deploy.py` + `run_v2_benchmark.py` workflow.

See `docs/bring-your-own-data.md` and `docs/data-pipeline-rebuild.md` for detailed instructions.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SEMHUB_LAYER` | `L3` | Which tier to activate |
| `SEMHUB_REGION` | `us-west-2` | AWS region |
| `SEMHUB_GRAPH_ID` | `<your-graph-id>` | Neptune Analytics graph identifier |
| `SEMHUB_ATHENA_DB` | `oncology_semantic_hub` | Athena database for patient data |
| `SEMHUB_RAW_DB` | `oncology_semantic_hub_raw` | Athena database for flat PrimeKG (L2) |
| `SEMHUB_RODA_DB` | `oncology_semantic_hub_roda` | Athena database for RODA tables |
| `SEMHUB_SUBJECT_MODEL` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Bedrock model ID |
| `SEMHUB_TEMP` | `0.0` | Inference temperature |
| `SEMHUB_KB_ID` | (from SSM) | Bedrock Knowledge Base ID |
| `SEMHUB_OLS_SSM_PREFIX` | `/app/ontology-lookup-service/agentcore` | SSM prefix for OLS config |
