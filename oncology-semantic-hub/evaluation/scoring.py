"""Scoring for the validation framework.

Two families of scoring:

1. Deterministic, code-based (AUTHORITATIVE for quantitative / list / ontology /
   regex answer types). No LLM in the loop — reproducible and cheap.
2. LLM-judge routing hook (for reasoning / multi_hop only). This module decides
   which answers need the judge (see needs_judge); the judge call lives in
   run_evaluation.py.

Plus reproducibility metrics across N runs:
- self_consistency:        do the N runs agree with each other? (determinism signal)
- reproducible_correctness: are all N runs correct AND identical? (customer number)
These are reported SEPARATELY so a consistently-wrong-but-stable answer is not
confused with a consistently-right one.

Robustness notes (fixes from independent QA/review):
- Predictions are usually PROSE, so entity recall is matched by substring on the
  alphanumeric-normalized prediction, not by delimiter tokenization alone.
- Numbers are extracted UNSIGNED (biomedical counts are non-negative) so hyphens
  in ranges/coordinates (chr14:100-200) are not misread as negatives.
- Expected answers stored as JSON strings are parsed and compared by VALUES only
  (JSON keys never contribute digits/entities).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass

DETERMINISTIC_TYPES = {"exact_number", "entity_list", "ranked_list", "ontology", "structured"}
JUDGE_TYPES = {"reasoning", "multi_hop", "text"}

_REFUSAL_PATTERNS = [
    r"\bi (?:do not|don't) have access\b",
    r"\bi (?:do not|don't) know\b",
    r"\bi (?:cannot|can't|am unable to) (?:determine|answer|provide|access)\b",
    r"\bunable to (?:determine|answer|access)\b",
    r"\bno (?:information|data) (?:available|found)\b",
    r"\bcannot be determined\b",
    r"\binsufficient (?:information|data)\b",
    # absence of an entity in the hub (cross-system misalignment / gene-gap probes)
    r"\bnot (?:present|found|in) (?:the )?(?:knowledge )?graph\b",
    r"\bnot (?:present|found|available) in the (?:hub|knowledge graph)\b",
    r"\bno (?:such )?(?:gene|node|entry|match)\b",
    r"\b(?:absent|missing) from the (?:graph|hub|knowledge graph)\b",
    r"\b(?:0|no|zero) drug(?:_protein)? (?:edges|targets|connections)\b",
]

# Generic words filtered out of prediction tokens so prose does not tank precision.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "via",
    "is", "are", "was", "were", "be", "that", "this", "these", "those", "there",
    "here", "it", "they", "them", "as", "by", "at", "from", "gene", "genes",
    "drug", "drugs", "disease", "diseases", "pathway", "pathways", "following",
    "include", "includes", "included", "list", "answer", "connected", "count",
    "number", "distinct", "total", "patients", "mutations", "results", "which",
}
_STOP_NORM = {re.sub(r"[^a-z0-9]+", "", w) for w in _STOPWORDS}


# ── helpers ──────────────────────────────────────────────────────────────────
def detect_refusal(text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t) for p in _REFUSAL_PATTERNS)


def _extract_numbers(text) -> list[float]:
    """Unsigned integers/decimals; thousands separators removed. Hyphens are NOT
    treated as minus signs (ranges/coordinates stay positive)."""
    cleaned = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(text))
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", cleaned)]


def _normalize_entity(s) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def _json_scalars(obj) -> list:
    """Recursively collect scalar VALUES from a parsed JSON object (keys ignored)."""
    out: list = []
    if isinstance(obj, dict):
        for v in obj.values():
            out += _json_scalars(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out += _json_scalars(v)
    else:
        out.append(obj)
    return out


def _parse_expected(expected) -> list:
    """Expected -> list of scalar values. Parses JSON strings; falls back to raw."""
    if isinstance(expected, (dict, list, tuple)):
        return _json_scalars(expected)
    s = str(expected).strip()
    if s[:1] in ("[", "{"):
        try:
            return _json_scalars(json.loads(s))
        except json.JSONDecodeError:
            pass
    return [expected]


def _expected_entities(expected) -> list[str]:
    """Expected -> flat list of entity strings (splitting any delimited scalars)."""
    ents: list[str] = []
    for s in _parse_expected(expected):
        if isinstance(s, str):
            ents += re.split(r"[,\n;]+", s)
        else:
            ents.append(str(s))
    return [e for e in ents if _normalize_entity(e)]


def _pred_tokens(prediction) -> set[str]:
    """Normalized, stopword-filtered tokens from a prediction (delimiters + whitespace)."""
    raw = re.split(r"[,\n;•|/]+|\s+|(?<=\d)-(?=\d)", str(prediction).lower())
    norm = {_normalize_entity(t) for t in raw}
    return {t for t in norm if t and t not in _STOP_NORM}


# ── deterministic scorers (return 0.0 / 0.5 / 1.0) ───────────────────────────
def score_exact_number(prediction, expected, tolerance: float = 0.10) -> float:
    """1.0 if the target appears exactly in the prediction, 0.5 within relative
    tolerance, else 0.0. Target = first numeric VALUE of expected (JSON-aware)."""
    exp_nums: list[float] = []
    for s in _parse_expected(expected):
        if isinstance(s, bool):
            continue
        if isinstance(s, (int, float)):
            exp_nums.append(float(s))
        else:
            exp_nums += _extract_numbers(s)
    pred_nums = _extract_numbers(prediction)
    if not exp_nums or not pred_nums:
        return 0.0
    target = exp_nums[0]
    if any(p == target for p in pred_nums):
        return 1.0
    denom = abs(target) if target != 0 else 1.0
    if min(abs(p - target) for p in pred_nums) / denom <= tolerance:
        return 0.5
    return 0.0


def f1_entities(prediction, expected) -> float:
    exp_norm = {_normalize_entity(e) for e in _expected_entities(expected)}
    exp_norm.discard("")
    if not exp_norm:
        return 0.0
    # recall: expected entity present as substring in the normalized prediction
    blob = _normalize_entity(prediction)
    recall = sum(1 for e in exp_norm if e in blob) / len(exp_norm)
    # precision: over stopword-filtered prediction tokens (only when list-like)
    ptoks = _pred_tokens(prediction)
    if ptoks:
        tp = sum(1 for t in ptoks if t in exp_norm)
        precision = tp / len(ptoks)
    else:
        precision = recall
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def recall_entities(prediction, expected) -> float:
    """Fraction of expected entities present (substring) in the normalized
    prediction. Robust to prose answers."""
    exp_norm = {_normalize_entity(e) for e in _expected_entities(expected)}
    exp_norm.discard("")
    if not exp_norm:
        return 0.0
    blob = _normalize_entity(prediction)
    return sum(1 for e in exp_norm if e in blob) / len(exp_norm)


def score_entity_list(prediction, expected) -> float:
    """Correctness = completeness (recall) of the expected entity set. Over-listing /
    hallucinated extras are NOT penalized here — that is the job of the separate
    faithfulness metric (Runtime phase). Precision is available via f1_entities()."""
    r = recall_entities(prediction, expected)
    if r > 0.8:
        return 1.0
    if r > 0.4:
        return 0.5
    return 0.0


def score_ranked_list(prediction, expected, k: int | None = None) -> float:
    """Top-k recall of expected items appearing (substring) in the prediction."""
    exp = [_normalize_entity(e) for e in _expected_entities(expected)]
    exp = [e for e in exp if e]
    if not exp:
        return 0.0
    k = len(exp) if k is None else k
    if k <= 0:
        return 0.0
    exp_topk = exp[:k]
    blob = _normalize_entity(prediction)
    overlap = sum(1 for e in exp_topk if e in blob) / len(exp_topk)
    if overlap > 0.8:
        return 1.0
    if overlap > 0.4:
        return 0.5
    return 0.0


def score_regex(prediction, pattern: str) -> float:
    if not pattern:
        return 0.0
    try:
        return 1.0 if re.search(pattern, str(prediction), re.IGNORECASE) else 0.0
    except re.error:
        return 0.0


def _assertion_satisfied(prediction, assertion) -> bool:
    """A pure-number assertion requires that exact number in the prediction; any
    other assertion requires its normalized text as a substring."""
    a = str(assertion).strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?", a):
        return float(a) in _extract_numbers(prediction)
    return _normalize_entity(a) in _normalize_entity(prediction)


def score_assertions(prediction, assertions) -> float:
    """ALL assertions must hold for full credit (used by composite / cross-system
    questions so a partial match — e.g. the gene but not the drug count — cannot
    score as correct). 1.0 all, 0.5 at least half, else 0.0."""
    if not assertions:
        return 0.0
    hits = sum(1 for a in assertions if _assertion_satisfied(prediction, a))
    frac = hits / len(assertions)
    return 1.0 if frac == 1 else (0.5 if frac >= 0.5 else 0.0)


def score_deterministic(answer_type: str, prediction, expected, *,
                        answer_regex: str = "", k: int | None = None,
                        assertions=None) -> float:
    """Route to the right deterministic scorer. Regex wins when present."""
    if answer_regex:
        return score_regex(prediction, answer_regex)
    if answer_type == "negative":
        # Negative control: correct iff the agent refuses / says it cannot determine.
        return 1.0 if detect_refusal(prediction) else 0.0
    if answer_type == "composite":
        return score_assertions(prediction, assertions or [])
    if answer_type == "exact_number":
        return score_exact_number(prediction, expected)
    if answer_type == "entity_list":
        return score_entity_list(prediction, expected)
    if answer_type == "ranked_list":
        return score_ranked_list(prediction, expected, k=k)
    if answer_type in ("ontology", "structured"):
        return score_entity_list(prediction, expected)
    return 0.0  # unknown -> defer to judge


def needs_judge(answer_type: str, answer_regex: str = "") -> bool:
    if answer_regex:
        return False
    return answer_type in JUDGE_TYPES


# ── reproducibility across N runs ────────────────────────────────────────────
@dataclass
class ReproResult:
    n_runs: int
    self_consistency: float
    all_consistent: bool
    reproducible_correct: bool
    mean_correctness: float

    def as_dict(self) -> dict:
        return {
            "n_runs": self.n_runs,
            "self_consistency": round(self.self_consistency, 3),
            "all_consistent": self.all_consistent,
            "reproducible_correct": self.reproducible_correct,
            "mean_correctness": round(self.mean_correctness, 3),
        }


def _answer_signature(text: str, answer_type: str | None = None,
                      expected=None, assertions=None) -> str:
    """Canonical signature keyed on the ANSWER VALUE (GT-relevant content), not prose,
    so run-to-run wording variation does not look like non-determinism. Value-anchored to
    `expected`/`assertions` when available."""
    t = text or ""
    if answer_type == "negative":
        return "refused" if detect_refusal(t) else "answered"
    if answer_type == "composite":
        asrt = assertions or []
        return "c:" + ",".join(str(i) for i, a in enumerate(asrt) if _assertion_satisfied(t, a))
    if answer_type == "exact_number" and expected is not None:
        exp_nums: list[float] = []
        for s in _parse_expected(expected):
            if isinstance(s, bool):
                continue
            if isinstance(s, (int, float)):
                exp_nums.append(float(s))
            else:
                exp_nums += _extract_numbers(s)
        if exp_nums:
            return "n:hit" if exp_nums[0] in _extract_numbers(t) else "n:miss"
    if answer_type in ("entity_list", "ranked_list", "ontology", "structured") and expected is not None:
        blob = _normalize_entity(t)
        present = [_normalize_entity(e) for e in _expected_entities(expected)]
        present = [e for e in present if e and e in blob]
        return "e:" + (",".join(present) if answer_type == "ranked_list" else ",".join(sorted(present)))
    # fallback (no expected, or reasoning/text): numbers if present else tokens
    nums = _extract_numbers(t)
    if nums:
        return "n:" + (str(nums[0]) if answer_type == "exact_number"
                       else ",".join(str(x) for x in sorted(nums)))
    return "e:" + ",".join(sorted(_pred_tokens(t)))


def reproducibility(answers: list[str], correctness_scores: list[float],
                    threshold: float, answer_type: str | None = None,
                    expected=None, assertions=None) -> ReproResult:
    """answers and correctness_scores are aligned per-run lists.
    self_consistency = answer-VALUE stability; reproducible_correct = all runs correct AND
    value-consistent."""
    n = len(answers)
    if n == 0:
        return ReproResult(0, 0.0, False, False, 0.0)
    sigs = [_answer_signature(a, answer_type, expected, assertions) for a in answers]
    _, modal_count = Counter(sigs).most_common(1)[0]
    all_correct = all(s >= threshold for s in correctness_scores)
    return ReproResult(
        n_runs=n,
        self_consistency=modal_count / n,
        all_consistent=len(set(sigs)) == 1,
        reproducible_correct=bool(len(set(sigs)) == 1 and all_correct),
        mean_correctness=sum(correctness_scores) / n,
    )
