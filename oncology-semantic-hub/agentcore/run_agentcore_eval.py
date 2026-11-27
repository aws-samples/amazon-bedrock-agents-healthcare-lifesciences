"""Run native AgentCore Evaluations against the deployed Oncology Semantic Hub Runtime.

Converts evaluation/golden_dataset.json into AgentCore dataset scenarios (ReferenceInputs:
expected_response / expected_trajectory / assertions) and runs the built-in evaluators via
OnDemandEvaluationDatasetRunner against the deployed agent's OTel traces.

Built-ins used:
  Builtin.Correctness           (TRACE, expected_response)   — is the answer right?
  Builtin.Faithfulness          (TRACE, trace)               — grounded in tool outputs? (hallucination)
  Builtin.ToolSelectionAccuracy (SESSION)                    — right tools chosen?
  Builtin.GoalSuccessRate       (SESSION, assertions)        — composite gene+count etc.
  Builtin.TrajectoryAnyOrderMatch (SESSION, expected_trajectory)

Prereq: agent deployed (agentcore/agent_config.json) + CloudWatch Transaction Search ACTIVE.

Usage:
    python run_agentcore_eval.py --limit 6
    python run_agentcore_eval.py --ids q_onto_01 q_misalign_05 q_drug_02
"""
import argparse
import json
import uuid
from pathlib import Path

import boto3
from botocore.config import Config
from bedrock_agentcore.evaluation import (
    AgentInvokerInput, AgentInvokerOutput, CloudWatchAgentSpanCollector,
    Dataset, EvaluationRunConfig, EvaluatorConfig, OnDemandEvaluationDatasetRunner,
    PredefinedScenario, Turn,
)

_DIR = Path(__file__).parent
_CFG = json.loads((_DIR / "agent_config.json").read_text())
_GOLDEN = _DIR.parent / "ground_truth" / "golden_dataset_v1.json"
_OUT = _DIR / "agentcore_eval_results.json"

EVALUATORS = [
    "Builtin.Correctness",
    "Builtin.Faithfulness",
    "Builtin.ToolSelectionAccuracy",
    "Builtin.GoalSuccessRate",
    "Builtin.TrajectoryAnyOrderMatch",
]

_rt = boto3.client("bedrock-agentcore", region_name=_CFG["region"],
                   config=Config(read_timeout=300, connect_timeout=15, retries={"max_attempts": 0}))


_ANSWERS = {}
try:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evaluation"))
    from provenance_faithfulness import score_provenance as _score_prov
except Exception:
    _score_prov = None


def agent_invoker(inp: AgentInvokerInput) -> AgentInvokerOutput:
    """Invoke the deployed Runtime agent for one scenario turn."""
    # AgentCore requires runtimeSessionId >= 33 chars; use the SDK session id, pad if needed.
    sid = inp.session_id or uuid.uuid4().hex + uuid.uuid4().hex
    if len(sid) < 33:
        sid = (sid + uuid.uuid4().hex)[:40]
    resp = _rt.invoke_agent_runtime(
        agentRuntimeArn=_CFG["agent_arn"], runtimeSessionId=sid,
        payload=json.dumps({"prompt": inp.payload}).encode())
    body = resp["response"].read().decode() if hasattr(resp["response"], "read") else resp["response"]
    try:
        text = json.loads(body)
        if not isinstance(text, str):
            text = json.dumps(text)
    except (json.JSONDecodeError, TypeError):
        text = body
    _ANSWERS[inp.payload] = text
    return AgentInvokerOutput(agent_output=text)


def build_dataset(questions) -> Dataset:
    scenarios = []
    for q in questions:
        eri = q["evaluationReferenceInputs"]
        scenarios.append(PredefinedScenario(
            scenario_id=q["id"],
            turns=[Turn(input=q["input"], expected_response=eri.get("expectedResponse"))],
            assertions=eri.get("assertions") or None,
            expected_trajectory=eri.get("expectedTrajectory") or None,
            metadata={"category": q["metadata"]["category"], "answer_type": q["metadata"]["answer_type"]},
        ))
    return Dataset(scenarios=scenarios)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None, help="agent config json (defaults to agent_config.json = L3)")
    ap.add_argument("--dataset", default=None, help="path to a dataset json (defaults to golden_dataset.json)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--evaluators", nargs="*", default=EVALUATORS)
    ap.add_argument("--delay", type=int, default=180, help="seconds to wait for span ingestion")
    args = ap.parse_args()

    global _CFG
    if args.config:
        _CFG = json.loads(Path(args.config).read_text())
        print(f"Target agent: {_CFG['agent_arn'].split('/')[-1]}")

    src = Path(args.dataset) if args.dataset else _GOLDEN
    _aid = _CFG["agent_arn"].split("/")[-1]
    _tag = ("_l0web" if "_l0_web_" in _aid else "_l3a" if "_l3a_" in _aid else "_l3b" if "_l3b_" in _aid
            else "_l1" if "_l1_" in _aid else "_l3" if "_l3_" in _aid else "_l0" if "_l0_" in _aid else "")
    _LAYER = "L0" if "_l0_" in _aid else ("L1" if "_l1_" in _aid else ("L3" if "_l3_" in _aid else "L2"))
    out_path = (_DIR / (src.stem + _tag + "_eval_results.json")) if (args.dataset or args.config) else _OUT
    gold = json.loads(src.read_text())
    if args.ids:
        gold = [q for q in gold if q["id"] in set(args.ids)]
    elif args.limit:
        gold = gold[:args.limit]
    print(f"Scenarios: {len(gold)}  evaluators: {args.evaluators}")
    _gin = {q["id"]: q.get("input") for q in gold}

    runner = OnDemandEvaluationDatasetRunner(region=_CFG["region"])
    result = runner.run(
        config=EvaluationRunConfig(
            evaluator_config=EvaluatorConfig(evaluator_ids=args.evaluators),
            evaluation_delay_seconds=args.delay),
        dataset=build_dataset(gold),
        agent_invoker=agent_invoker,
        span_collector=CloudWatchAgentSpanCollector(
            log_group_name=_CFG["cw_log_group"], region=_CFG["region"]),
    )

    # Persist + print per-scenario, per-evaluator scores.
    # EvaluatorResult.results is a list of dicts (EvaluatorOutput: value/label/explanation/errorMessage).
    out = []
    for sr in getattr(result, "scenario_results", []) or []:
        row = {"scenario_id": getattr(sr, "scenario_id", "?"),
               "status": getattr(sr, "status", None),
               "error": getattr(sr, "error", None), "scores": {}}
        for ev in getattr(sr, "evaluator_results", []) or []:
            recs = getattr(ev, "results", []) or []
            vals = [r.get("value") for r in recs if isinstance(r, dict) and r.get("value") is not None]
            labels = [r.get("label") for r in recs if isinstance(r, dict) and r.get("label")]
            errs = [r.get("errorMessage") for r in recs if isinstance(r, dict) and r.get("errorMessage")]
            row["scores"][getattr(ev, "evaluator_id", "?")] = {
                "value": vals[0] if vals else None,
                "label": labels[0] if labels else None,
                "error": errs[0] if errs else None,
            }
        _ans = _ANSWERS.get(_gin.get(row["scenario_id"]))
        row["answer"] = _ans
        if _ans is not None and _score_prov is not None:
            _pv = _score_prov(_ans, _LAYER)
            row["scores"]["Provenance.Faithfulness"] = {"value": _pv["provenance_faithfulness"],
                "label": f"grounding={_pv['grounding_rate']};fab={_pv['fabricated']}", "error": None}
        out.append(row)
        print(f"  {row['scenario_id']:<16} " +
              " ".join(f"{k.split('.')[-1]}={v['value'] if v['value'] is not None else v['label'] or v['error']}"
                       for k, v in row["scores"].items()))
    out_path.write_text(json.dumps({"results": out}, indent=2, default=str))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
