"""L1-vs-L3 layer runner for the Semantic Hub Validation Framework.

Reuses evaluation.config (C), evaluation.scoring (S), and evaluation.hub_tools
(TOOLS + strands BedrockModel). L1 is the raw data lake (Athena SQL, no semantic
map); L3 is the full semantic hub (strands Agent with Neptune/Athena tools). The
runner is config-driven: any layer in C.LAYERS with no tools runs as a bare LLM,
otherwise as a tool-using agent.

Per question per layer: 1 deterministic correctness run + N_RUNS reproducibility
runs at a non-zero temperature. Deterministic scoring only (no judge). Writes
results/pilot_results.json (or pilot_results_smoke.json under --smoke).

    python -m evaluation.run_evaluation --smoke --limit 1
    python -m evaluation.run_evaluation
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import boto3
from strands import Agent
from strands.models import BedrockModel
from strands.types.exceptions import MaxTokensReachedException

from . import config as C
from . import hub_tools
from . import scoring as S

_bedrock = boto3.client("bedrock-runtime", region_name=C.REGION)

_PROMPTS = {
    name: (C.SYSTEM_PROMPTS_DIR / layer.system_prompt_file).read_text()
    for name, layer in C.LAYERS.items()
}


def _message_text(message: dict) -> str:
    """Concatenate text blocks from a strands/converse message."""
    return "".join(
        b["text"] for b in message.get("content", []) if isinstance(b, dict) and "text" in b
    ).strip()


def _run_layer(layer_name: str, question: str, temperature: float) -> tuple[str, list[str], float]:
    """Config-driven: no tools -> bare LLM (direct converse); tools -> strands Agent
    with the layer's tool set, capturing the tool trajectory."""
    layer = C.LAYERS[layer_name]
    prompt = _PROMPTS[layer_name]

    if not layer.tools:
        t0 = time.time()
        resp = _bedrock.converse(
            modelId=C.SUBJECT_MODEL_ID,
            system=[{"text": prompt}],
            messages=[{"role": "user", "content": [{"text": question}]}],
            inferenceConfig={"temperature": temperature, "maxTokens": C.MAX_TOKENS},
        )
        return _message_text(resp["output"]["message"]), [], time.time() - t0

    tools_called: list[str] = []

    def _record(**kwargs):
        cur = kwargs.get("current_tool_use") or {}
        name = cur.get("name")
        if name and (not tools_called or tools_called[-1] != name):
            tools_called.append(name)

    agent = Agent(
        model=BedrockModel(
            model_id=C.SUBJECT_MODEL_ID,
            region_name=C.REGION,
            temperature=temperature,
            max_tokens=C.MAX_TOKENS,
        ),
        tools=[hub_tools.TOOLS[name] for name in layer.tools],
        system_prompt=prompt,
        callback_handler=_record,
    )
    t0 = time.time()
    try:
        result = agent(question)
        answer = _message_text(result.message)
    except MaxTokensReachedException:
        # Model hit max_tokens mid-trajectory (often truncating a tool call).
        # Record whatever trajectory was captured and let scoring handle the
        # empty/partial answer (typically 0) instead of aborting the chunk.
        answer = ""
    return answer, tools_called, time.time() - t0


def _one_run(layer_name: str, question: str, temperature: float,
             answer_type: str, expected, answer_regex: str, assertions=None) -> dict:
    answer, tools_called, elapsed = _run_layer(layer_name, question, temperature)
    if answer_type == "negative":
        from . import judge
        score = judge.judge_absence(question, answer, str(expected))
    else:
        score = S.score_deterministic(answer_type, answer, expected,
                                      answer_regex=answer_regex, assertions=assertions)
    return {
        "answer": answer,
        "tools_called": tools_called,
        "elapsed_sec": round(elapsed, 2),
        "score": score,
        "refused": S.detect_refusal(answer),
    }


def _eval_layer(layer_name: str, q: dict, n_repro: int) -> dict:
    meta = q["metadata"]
    answer_type = meta["answer_type"]
    answer_regex = meta.get("answer_regex", "")
    expected = q["evaluationReferenceInputs"]["expectedResponse"]
    assertions = q["evaluationReferenceInputs"].get("assertions", [])
    question = q["input"]

    correctness = _one_run(layer_name, question, C.CORRECTNESS_TEMPERATURE,
                           answer_type, expected, answer_regex, assertions)
    print(f"    {layer_name} correctness: score={correctness['score']} "
          f"tools={correctness['tools_called']} {correctness['elapsed_sec']}s")

    repro_runs = []
    for i in range(n_repro):
        r = _one_run(layer_name, question, C.REPRODUCIBILITY_TEMPERATURE,
                     answer_type, expected, answer_regex, assertions)
        print(f"    {layer_name} repro[{i + 1}/{n_repro}]: score={r['score']} "
              f"tools={r['tools_called']} {r['elapsed_sec']}s")
        repro_runs.append(r)

    repro = S.reproducibility([r["answer"] for r in repro_runs],
                             [r["score"] for r in repro_runs],
                             C.CORRECTNESS_THRESHOLD, answer_type,
                             expected=expected, assertions=assertions)
    return {
        "correctness_run": correctness,
        "reproducibility_runs": repro_runs,
        "is_correct": correctness["score"] >= C.CORRECTNESS_THRESHOLD,
        "reproducibility": repro.as_dict(),
    }


def _summarize(questions: list[dict], layer_name: str) -> dict:
    layers = [q["layers"][layer_name] for q in questions]
    n = len(layers)
    if n == 0:
        return {"n": 0, "correctness_pct": 0.0, "reproducibility_pct": 0.0, "mean_correctness": 0.0}
    correct = sum(1 for l in layers if l["is_correct"])
    reproducible = sum(1 for l in layers if l["reproducibility"]["reproducible_correct"])
    mean_corr = sum(l["reproducibility"]["mean_correctness"] for l in layers) / n
    mean_elapsed = sum(l["correctness_run"]["elapsed_sec"] for l in layers) / n
    return {
        "n": n,
        "correctness_pct": round(correct / n, 3),
        "reproducibility_pct": round(reproducible / n, 3),
        "mean_correctness": round(mean_corr, 3),
        "mean_elapsed_sec": round(mean_elapsed, 2),
    }


def main():
    ap = argparse.ArgumentParser(description="L0-vs-L3 layer runner")
    ap.add_argument("--smoke", action="store_true",
                    help="1 question, 1 run per phase; writes pilot_results_smoke.json")
    ap.add_argument("--limit", type=int, default=None, help="cap number of questions")
    ap.add_argument("--resume", action="store_true",
                    help="reuse already-evaluated questions from the existing results file")
    ap.add_argument("--start", type=int, default=0, help="slice start index into the dataset")
    ap.add_argument("--end", type=int, default=None, help="slice end index into the dataset")
    ap.add_argument("--out", default=None, help="output filename under results/ (for parallel chunks)")
    args = ap.parse_args()

    with open(C.GOLDEN_DATASET) as f:
        dataset = json.load(f)

    limit = 1 if args.smoke else args.limit
    if limit is not None:
        dataset = dataset[:limit]
    if args.start or args.end is not None:
        dataset = dataset[args.start:args.end]
    n_repro = 1 if args.smoke else C.N_RUNS

    layer_names = list(C.LAYERS.keys())
    if args.smoke:
        out_path = C.RESULTS_DIR / "pilot_results_smoke.json"
    elif args.out:
        out_path = C.RESULTS_DIR / args.out
    else:
        out_path = C.RESULTS_DIR / "pilot_results.json"

    def _write(questions):
        out = {
            "meta": {
                "snapshot": C.DATA_SNAPSHOT,
                "subject_model": C.SUBJECT_MODEL_ID,
                "layers": layer_names,
                "n_reproducibility_runs": n_repro,
                "correctness_temperature": C.CORRECTNESS_TEMPERATURE,
                "reproducibility_temperature": C.REPRODUCIBILITY_TEMPERATURE,
                "threshold": C.CORRECTNESS_THRESHOLD,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "questions": questions,
            "summary": {ln: _summarize(questions, ln) for ln in layer_names},
        }
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        return out

    # Resume: reuse already-evaluated questions from a prior (interrupted) run.
    done = {}
    if args.resume and out_path.exists():
        prior = json.load(open(out_path))
        done = {q["id"]: q for q in prior.get("questions", [])}
        print(f"Resuming: {len(done)} question(s) already evaluated.")

    questions = []
    for q in dataset:
        if q["id"] in done:
            questions.append(done[q["id"]])
            print(f"[{q['id']}] (cached)")
            continue
        meta = q["metadata"]
        print(f"[{q['id']}] {q['input'][:70]}")
        entry = {
            "id": q["id"],
            "input": q["input"],
            "category": meta["category"],
            "answer_type": meta["answer_type"],
            "required_layers": meta["required_layers"],
            "complexity": meta["complexity"],
            "expected": q["evaluationReferenceInputs"]["expectedResponse"],
            "layers": {ln: _eval_layer(ln, q, n_repro) for ln in layer_names},
        }
        questions.append(entry)
        _write(questions)  # checkpoint after each question

    out = _write(questions)
    print(f"\nSummary: {json.dumps(out['summary'])}")
    print(f"Wrote {len(questions)} questions -> {out_path}")


if __name__ == "__main__":
    main()
