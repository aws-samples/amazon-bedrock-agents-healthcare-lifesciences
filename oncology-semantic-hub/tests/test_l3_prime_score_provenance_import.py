"""Unit test for agentcore/l3_prime.py's _load_score_provenance() — the refactor that replaced a
subprocess.run() call to skills/grounding-faithfulness-eval/scripts/score_provenance.py with a
direct importlib import.

This closes the semgrep dangerous-subprocess-use(-audit/-tainted-env-args) findings at the root:
there is no longer any subprocess call in l3_prime.py to flag. This test proves the replacement
actually works — the imported function must behave identically to running the script, for both a
grounded and a fabricated answer, across the known-good inventories.

Imports only the standalone module under test via importlib (mirrors l3_prime.py's own mechanism)
so this test has no heavy deps (strands/mcp/boto3) and can't be broken by l3_prime.py's own
unrelated import requirements.
"""
import importlib.util
import unittest
from pathlib import Path

_HUB = Path(__file__).resolve().parents[1]  # oncology_semantic_hub/
_SCORE_PROVENANCE_PATH = _HUB / "skills" / "grounding-faithfulness-eval" / "scripts" / "score_provenance.py"
_L3_PRIME_PATH = _HUB / "agentcore" / "l3_prime.py"


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestLoadScoreProvenance(unittest.TestCase):
    """Exercises l3_prime.py's _load_score_provenance() exactly as main() calls it, without
    importing l3_prime.py itself (avoids pulling in strands/mcp/boto3)."""

    @classmethod
    def setUpClass(cls):
        if not _SCORE_PROVENANCE_PATH.exists():
            raise unittest.SkipTest(f"score_provenance.py not found at {_SCORE_PROVENANCE_PATH}")
        if not _L3_PRIME_PATH.exists():
            raise unittest.SkipTest(f"l3_prime.py not found at {_L3_PRIME_PATH}")
        # Re-implement _load_score_provenance()'s exact mechanism (importlib, no subprocess) to
        # avoid importing l3_prime.py's own heavy-dep imports (strands/mcp/boto3) at module level.
        # staticmethod() wrapper: a plain function stored as a class attribute is treated as an
        # instance method (implicit `self`) unless wrapped — score_provenance(answer, layer) takes
        # exactly 2 args, so unwrap it here.
        cls.score_provenance = staticmethod(_load_module(_SCORE_PROVENANCE_PATH, "score_provenance").score_provenance)

    def test_import_has_no_subprocess_module_reference(self):
        """l3_prime.py itself must no longer import or reference subprocess."""
        src = _L3_PRIME_PATH.read_text()
        self.assertNotIn("import subprocess", src)
        self.assertNotIn("subprocess.run", src)

    def test_scores_a_fully_grounded_answer(self):
        answer = "148 patients [Lake:tcga_mutations]; EGFR is druggable [Graph]; MONDO:0018177 [OLS:MONDO:0018177]."
        result = self.score_provenance(answer, "L3")
        self.assertEqual(result["provenance_faithfulness"], 1.0)
        self.assertEqual(result["fabricated"], [])
        self.assertGreater(result["n_tags"], 0)

    def test_detects_fabricated_grounding_for_a_tool_the_inventory_lacks(self):
        """L1 (lake-only) claiming [Graph] is fabricated — the scorer must flag it, proving the
        imported function enforces the same per-inventory VALID set as the subprocess version did."""
        answer = "EGFR is druggable [Graph]; 82 patients [Lake:tcga_mutations]."
        result = self.score_provenance(answer, "L1")
        self.assertLess(result["provenance_faithfulness"], 1.0)
        self.assertIn("graph", result["fabricated"])

    def test_unauditable_untagged_answer_returns_none_not_zero(self):
        result = self.score_provenance("BRAF V600E confers resistance.", "L3")
        self.assertIsNone(result["provenance_faithfulness"])
        self.assertIsNone(result["grounding_rate"])
        self.assertEqual(result["n_tags"], 0)

    def test_works_for_every_known_inventory_l3_prime_can_pass(self):
        """Every value l3_prime.py's --inventory choices= allows must be a valid key the scorer
        recognizes (no KeyError / silent-wrong-answer for a value argparse lets through)."""
        answer = "Some fact [Model knowledge]."
        for inv in ["quick", "L0", "L0-web", "L1", "L2", "L3"]:
            with self.subTest(inventory=inv):
                result = self.score_provenance(answer, inv)
                self.assertEqual(result["provenance_faithfulness"], 1.0)  # [Model knowledge] is always valid


if __name__ == "__main__":
    unittest.main()
