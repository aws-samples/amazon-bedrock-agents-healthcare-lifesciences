"""Unit tests for evaluation.scoring — runnable without pytest:
    python -m evaluation.test_scoring
Exits non-zero on first failure.
"""
from __future__ import annotations

from evaluation import scoring as S


def check(name, got, want):
    assert got == want, f"FAIL {name}: got {got!r}, want {want!r}"
    print(f"  ok  {name}: {got}")


def test_exact_number():
    check("exact match", S.score_exact_number("187 distinct patients", "187"), 1.0)
    check("exact with commas", S.score_exact_number("1,234 cases", "1234"), 1.0)
    check("within 10%", S.score_exact_number("200", "187"), 0.5)
    check("outside 10%", S.score_exact_number("300", "187"), 0.0)
    check("no number in pred", S.score_exact_number("I don't know", "187"), 0.0)


def test_entity_list():
    check("full match", S.score_entity_list("TP53, EGFR, KRAS", ["TP53", "EGFR", "KRAS"]), 1.0)
    # 2 of 3 correct, no false positives -> F1=0.8 -> 0.5 band (thresholds are strict >)
    check("partial", S.score_entity_list("TP53, EGFR", ["TP53", "EGFR", "KRAS"]), 0.5)
    check("none", S.score_entity_list("nothing relevant here", ["TP53", "EGFR", "KRAS"]), 0.0)
    # F1 sanity
    f1 = S.f1_entities("TP53, EGFR", ["TP53", "EGFR", "KRAS", "PTEN"])
    assert 0.5 < f1 < 0.7, f1
    print(f"  ok  f1 partial = {f1:.3f}")


def test_ranked_list():
    check("top-k full", S.score_ranked_list("TP53, TTN, PIK3CA", ["TP53", "TTN", "PIK3CA"]), 1.0)
    check("top-k partial", S.score_ranked_list("TP53 only", ["TP53", "TTN", "PIK3CA", "MUC16", "KMT2C"]), 0.0)


def test_refusal():
    for t in ["I don't have access to that data", "This cannot be determined",
              "I don't know the exact count", "No data available for that gene"]:
        assert S.detect_refusal(t) is True, t
    for t in ["The answer is 187 patients", "TP53 is connected to 12 drugs"]:
        assert S.detect_refusal(t) is False, t
    print("  ok  refusal detection (4 positive, 2 negative)")


def test_regex():
    check("regex hit", S.score_regex("the value is 187", r"\b187\b"), 1.0)
    check("regex miss", S.score_regex("the value is 999", r"\b187\b"), 0.0)


def test_reproducibility():
    thr = 0.8
    # 3 identical, correct
    r = S.reproducibility(["187 patients", "187 patients", "187"], [1.0, 1.0, 1.0], thr)
    assert r.self_consistency == 1.0 and r.reproducible_correct is True, r
    print(f"  ok  identical-correct: {r.as_dict()}")
    # consistent but WRONG (all refusals, scored 0) — the key disambiguation
    r = S.reproducibility(["I don't know", "I don't know", "I don't know"], [0.0, 0.0, 0.0], thr)
    assert r.self_consistency == 1.0 and r.reproducible_correct is False, r
    print(f"  ok  consistent-but-wrong: {r.as_dict()}")
    # inconsistent answers
    r = S.reproducibility(["187", "205", "150"], [1.0, 0.0, 0.0], thr)
    assert r.all_consistent is False and r.reproducible_correct is False, r
    print(f"  ok  inconsistent: {r.as_dict()}")


def test_regression_bugfixes():
    """Regression tests for issues found by independent QA/review agents."""
    # prose predictions must not collapse into one token (whitespace tokenization)
    check("prose entity list", S.score_entity_list("The genes are TP53 EGFR KRAS",
                                                    ["TP53", "EGFR", "KRAS"]), 1.0)
    # hyphen in a range is not a minus sign; 200 is present -> exact
    check("hyphen range", S.score_exact_number("the range is 100-200", "200"), 1.0)
    # expected stored as a JSON string -> parse VALUES
    check("json expected number", S.score_exact_number("187", '{"count": 187}'), 1.0)
    # JSON KEY digits must not become the target (key 'sort1' -> not 1)
    check("json key digits ignored", S.score_exact_number("10.71", '{"sort1_score": 10.71}'), 1.0)
    # JSON entity value matched from prose
    check("json entity value", S.score_entity_list("The protein is P53920",
                                                    '{"uniprot_id": "P53920"}'), 1.0)
    # N=0 must not crash
    r = S.reproducibility([], [], 0.8)
    assert r.n_runs == 0 and r.reproducible_correct is False, r
    print(f"  ok  reproducibility N=0 no crash: {r.as_dict()}")
    # k=0 means top-0, not top-all
    check("ranked k=0", S.score_ranked_list("TP53, TTN", ["TP53", "TTN"], k=0), 0.0)
    # incidental trailing number must not split identical numeric answers
    r = S.reproducibility(["187 patients", "187 patients across 500 cohorts", "187"],
                          [1.0, 1.0, 1.0], 0.8, answer_type="exact_number")
    assert r.all_consistent is True, r
    print(f"  ok  numeric signature ignores incidental number: {r.as_dict()}")


def test_composite_assertions():
    """Cross-system composite scoring: gene AND count both required."""
    A = ["TP53", "8"]
    # full answer (gene + count) -> correct
    check("composite full", S.score_deterministic(
        "composite", "The most mutated gene in TCGA-LUAD is TP53, targeted by 8 drugs",
        None, assertions=A), 1.0)
    # gene only, no/wrong count (the L1 failure mode) -> 0.5, below 0.8 => NOT correct
    check("composite gene-only", S.score_deterministic(
        "composite", "The most mutated gene in TCGA-LUAD is TP53.", None, assertions=A), 0.5)
    # wrong gene and wrong count -> 0.0
    check("composite none", S.score_deterministic(
        "composite", "It is EGFR targeted by 31 drugs", None, assertions=A), 0.0)
    # gene token with digits must not be misread as a number requirement
    assert S._assertion_satisfied("the gene is TP53", "TP53") is True
    assert S._assertion_satisfied("no such gene here", "TP53") is False
    print("  ok  gene-with-digits assertion handled")


def test_negative_controls():
    # correct iff the agent refuses / says it cannot determine
    check("negative refusal", S.score_deterministic(
        "negative", "That cannot be determined from the hub; no such data is loaded.", None), 1.0)
    check("negative fabrication", S.score_deterministic(
        "negative", "The AJCC tumor stage is IIIA.", None), 0.0)


def main():
    tests = [test_exact_number, test_entity_list, test_ranked_list,
             test_refusal, test_regex, test_reproducibility, test_regression_bugfixes,
             test_composite_assertions, test_negative_controls]
    for t in tests:
        print(f"\n{t.__name__}:")
        t()
    print("\nALL SCORING TESTS PASSED")


# --- unittest adapter -------------------------------------------------------
# The assertions above are plain functions (runnable via `python -m evaluation.test_scoring`).
# This adapter also exposes them to `unittest discover` so a standard CI command runs them —
# previously these ~45 scorer assertions were invisible to the test runner (pre-PR testing review).
import unittest  # noqa: E402


class TestScoring(unittest.TestCase):
    """Discovers each module-level test_* function and runs it as a subTest."""

    def test_all_scoring_functions(self):
        fns = [v for k, v in sorted(globals().items())
               if k.startswith("test_") and callable(v)]
        self.assertTrue(fns, "no test_* functions found in evaluation.test_scoring")
        for fn in fns:
            with self.subTest(scorer=fn.__name__):
                fn()  # raises AssertionError on failure → reported per subTest


if __name__ == "__main__":
    main()
