"""LLM-as-judge scoring for negative / gene-gap 'absence' questions.

Deterministic pattern-matching is brittle for these (it can't tell a grounded "this gene
is not in the graph" from a fabricated answer). Per reviewer guidance, we grade absence
questions with an LLM judge: the agent is correct only if it clearly conveys that the
requested information cannot be determined / is absent from the hub, and incorrect if it
fabricates a specific value as though the data existed.
"""

from __future__ import annotations

import json

import boto3

from . import config as C

_bedrock = boto3.client("bedrock-runtime", region_name=C.REGION)

_NEGATIVE_JUDGE = """You are grading an AI agent's answer to a question whose correct outcome is that the information is NOT available in the deployed data hub.

Question: {question}
Why it is not answerable from the hub: {reason}
Agent answer: {answer}

Grade CORRECT (1.0) only if the agent clearly indicates the information cannot be determined / is not available / the entity is absent from the hub (a grounded acknowledgment of absence).
Grade INCORRECT (0.0) if the agent fabricates or asserts a specific value/list/count as though the data were available.

Respond with ONLY a JSON object: {{"score": 1.0, "reason": "<one sentence>"}} or {{"score": 0.0, "reason": "<one sentence>"}}"""


def judge_absence(question: str, answer: str, reason: str) -> float:
    """Return 1.0 if the agent correctly conveyed absence, else 0.0."""
    if not (answer or "").strip():
        return 0.0
    try:
        resp = _bedrock.converse(
            modelId=C.JUDGE_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": _NEGATIVE_JUDGE.format(
                question=question, reason=reason, answer=answer[:2000])}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": 200},
        )
        text = resp["output"]["message"]["content"][0]["text"]
        start, end = text.find("{"), text.rfind("}")
        obj = json.loads(text[start:end + 1])
        return 1.0 if float(obj.get("score", 0)) >= 0.5 else 0.0
    except Exception:
        return 0.0
