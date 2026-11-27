"""Real-time provenance metrics for the Oncology Semantic Hub agent.

TWO metrics are computable at RESPONSE TIME from a single answer — no golden ground
truth, no extra LLM call, no multi-run aggregation (see docs/benchmark-report.md §12):

  • provenance_faithfulness — layer-aware attribution honesty. 1.0 = every provenance
    tag is one the layer's real tool inventory can produce; penalizes *fabricated
    grounding* (e.g. an L0 answer claiming [Lake], or L2 claiming [Graph]).
  • grounding_rate (descriptor) — fraction of tags that are tool-retrieved vs
    [Model knowledge]/[Recalled] parametric memory.

Both are pure functions of the answer's provenance tags + the tier's known tool
inventory, so they can be surfaced to a user immediately after the agent responds.
(Correctness needs verified ground truth; reproducibility needs N runs — both stay batch.)

This module reuses the CANONICAL scorer (evaluation/provenance_faithfulness.py) so the
real-time numbers match the batch report exactly, then emits to CloudWatch — the store
behind AgentCore observability — via one of two paths:

  • emit_cloudwatch(...)  — boto3 PutMetricData with an EXPLICIT timestamp. Use this from
    the demo UI (timestamp = agent-invocation time, mode="realtime") and from the batch
    job (timestamp = batch-job time, mode="batch"). Client-side; needs cloudwatch:PutMetricData.
  • emit_emf(...)         — prints an Embedded Metric Format (EMF) log line. Use this from
    INSIDE the AgentCore runtime, where stdout already flows to CloudWatch Logs and no extra
    IAM permission is required; CloudWatch auto-extracts the metrics from the EMF blob.

cf. 06-observe-evaluate-optimize-your-agent/01-observe (AgentCore observability = CloudWatch).
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Reuse the canonical scorer so real-time == batch definitions.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from evaluation.provenance_faithfulness import score_provenance  # noqa: E402

logger = logging.getLogger(__name__)

NAMESPACE = "OncologySemanticHub/Metrics"

# metric-key -> (CloudWatch MetricName, Unit). Only keys present in the metrics dict are emitted.
_METRIC_SPECS = {
    "provenance_faithfulness": ("ProvenanceFaithfulness", "None"),
    "grounding_rate": ("GroundingRate", "None"),
    "n_tags": ("NTags", "Count"),
    # batch-only companions (emitted when supplied):
    "correctness": ("Correctness", "None"),
    "reproducibly_correct": ("ReproduciblyCorrect", "None"),
    "self_agreement": ("SelfAgreement", "None"),
}


def compute_realtime(answer: str, layer: str) -> dict:
    """Compute the real-time metrics for one agent response.

    Returns a dict with provenance_faithfulness, grounding_rate, n_tags, fabricated (list of
    fabricated tag types), and an optional note (e.g. "no provenance tags (unauditable)").
    Pure/deterministic — safe to call on the hot path.
    """
    s = score_provenance(answer or "", layer)
    n_tags = s.get("n_tags", 0)
    auditable = n_tags > 0
    # An UNTAGGED answer is *unauditable*, not dishonest — reporting 0.0 would conflate "no
    # evidence to check" with "fabricated grounding". Return None so the emit/aggregate paths
    # skip it (no false zero on dashboards, no downward bias on the batch mean).
    return {
        "layer": layer,
        "provenance_faithfulness": s.get("provenance_faithfulness", 0.0) if auditable else None,
        "grounding_rate": s.get("grounding_rate", 0.0) if auditable else None,
        "n_tags": n_tags,
        "fabricated": s.get("fabricated", []),
        "note": s.get("note"),
    }


def _dimensions(layer: str, mode: str, model: str | None, extra_dims: dict | None) -> list[dict]:
    dims = [{"Name": "Layer", "Value": layer}, {"Name": "Mode", "Value": mode}]
    if model:
        dims.append({"Name": "Model", "Value": model})
    for k, v in (extra_dims or {}).items():
        dims.append({"Name": str(k), "Value": str(v)})
    return dims


def _metric_data(metrics: dict, dims: list[dict], ts: datetime) -> list[dict]:
    data: list[dict] = []
    for key, (name, unit) in _METRIC_SPECS.items():
        v = metrics.get(key)
        if v is None:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        data.append({"MetricName": name, "Dimensions": dims, "Timestamp": ts, "Value": v, "Unit": unit})
    fab = metrics.get("fabricated")
    if fab is not None and metrics.get("provenance_faithfulness") is not None:
        count = len(fab) if isinstance(fab, (list, tuple, set)) else fab
        data.append({"MetricName": "FabricatedGroundingCount", "Dimensions": dims,
                     "Timestamp": ts, "Value": float(count), "Unit": "Count"})
    return data


def emit_cloudwatch(metrics: dict, *, layer: str, mode: str, timestamp: datetime | None = None,
                    region: str = "us-west-2", namespace: str = NAMESPACE,
                    model: str | None = None, extra_dims: dict | None = None, client=None) -> dict:
    """Publish metrics to CloudWatch with an EXPLICIT timestamp (best-effort — never raises).

    mode="realtime" -> timestamp should be the agent-invocation time.
    mode="batch"    -> timestamp should be the batch-job time.
    Returns {"emitted": <count>} (and "error" on failure). Metric computation is independent
    of emission, so a missing permission/credential degrades gracefully to display-only.
    """
    ts = timestamp or datetime.now(timezone.utc)
    dims = _dimensions(layer, mode, model, extra_dims)
    data = _metric_data(metrics, dims, ts)
    if not data:
        return {"emitted": 0, "note": "no numeric metrics to emit"}
    try:
        import boto3
        cw = client or boto3.client("cloudwatch", region_name=region)
        # PutMetricData accepts up to 1000 metrics/call; we send <10.
        cw.put_metric_data(Namespace=namespace, MetricData=data)
        logger.info("emitted %d metric(s) to %s [Layer=%s Mode=%s ts=%s]",
                    len(data), namespace, layer, mode, ts.isoformat())
        return {"emitted": len(data)}
    except Exception as e:  # noqa: BLE001  (observability must never break the agent/UI)
        logger.warning("CloudWatch emit failed (%s); metrics computed but not published", e)
        return {"emitted": 0, "error": str(e)}


def emf_dict(metrics: dict, *, layer: str, mode: str, timestamp: datetime | None = None,
             namespace: str = NAMESPACE, model: str | None = None) -> dict:
    """Build an Embedded Metric Format (EMF) record for the given metrics.

    Print the returned dict as JSON to stdout from inside the AgentCore runtime; CloudWatch
    Logs auto-extracts the declared metrics (no PutMetricData permission needed). EMF timestamp
    is epoch milliseconds.
    """
    ts = timestamp or datetime.now(timezone.utc)
    dim_keys = ["Layer", "Mode"] + (["Model"] if model else [])
    fields: dict = {"Layer": layer, "Mode": mode}
    if model:
        fields["Model"] = model
    definitions = []
    for key, (name, unit) in _METRIC_SPECS.items():
        v = metrics.get(key)
        if v is None:
            continue
        try:
            fields[name] = float(v)
        except (TypeError, ValueError):
            continue
        definitions.append({"Name": name, "Unit": unit})
    fab = metrics.get("fabricated")
    if fab is not None and metrics.get("provenance_faithfulness") is not None:
        fields["FabricatedGroundingCount"] = float(len(fab) if isinstance(fab, (list, tuple, set)) else fab)
        definitions.append({"Name": "FabricatedGroundingCount", "Unit": "Count"})
    return {
        "_aws": {
            "Timestamp": int(ts.timestamp() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": namespace,
                "Dimensions": [dim_keys],
                "Metrics": definitions,
            }],
        },
        **fields,
    }


def emit_emf(metrics: dict, **kwargs) -> dict:
    """Print an EMF record to stdout (for in-runtime emission). Returns the record."""
    rec = emf_dict(metrics, **kwargs)
    print(json.dumps(rec, default=str), flush=True)
    return rec


if __name__ == "__main__":
    # Self-test: compute real-time metrics on representative answers per layer.
    samples = [
        ("L3", "144 genes are associated with glioblastoma [Graph]; EGFR is druggable via erlotinib "
               "[Graph]; 82 TCGA-GBM patients carry an EGFR mutation [Lake:tcga_mutations]; "
               "glioblastoma resolves to [OLS:MONDO:0018177]."),
        ("L3", "EGFR drives GBM [Model knowledge]; ~500 genes are involved [Model knowledge]."),  # honest but ungrounded
        ("L2", "EGFR targets erlotinib [Graph]; 79 patients [Lake:tcga_mutations]."),  # FABRICATED: L2 has no graph
        ("L0", "148 TCGA-GBM patients carry EGFR [Lake:tcga_mutations]."),             # FABRICATED: L0 has no lake
        ("L0", "EGFR is a driver in GBM [Model knowledge]; erlotinib is a therapy [Recalled: NCCN]."),
        ("L3", "BRAF V600E confers resistance."),  # untagged -> unauditable
    ]
    for layer, ans in samples:
        m = compute_realtime(ans, layer)
        print(f"{layer}: provfaith={m['provenance_faithfulness']} grounding={m['grounding_rate']} "
              f"n_tags={m['n_tags']} fabricated={m['fabricated']}"
              + (f"  ({m['note']})" if m.get("note") else ""))
        # show the EMF record shape for the first sample
    print("\nEMF record example:")
    print(json.dumps(emf_dict(compute_realtime(samples[0][1], "L3"), layer="L3", mode="realtime"),
                     indent=2, default=str))
