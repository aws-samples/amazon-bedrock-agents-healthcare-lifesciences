"""Drift guard: the eval skill's bundled scorer MUST match the shipped real-time scorer
(agentcore/realtime_metrics.compute_realtime) so Quick-live numbers == batch report numbers.

Run: python -m tests.test_parity   (from skills/grounding-faithfulness-eval/)
  or: python skills/grounding-faithfulness-eval/tests/test_parity.py
"""
import importlib.util
import sys
import unittest
from pathlib import Path

_SKILL = Path(__file__).resolve().parents[1]           # skills/grounding-faithfulness-eval
_REPO = _SKILL.parents[1]                                # repo root
_HUB = _REPO / "oncology_semantic_hub"
sys.path.insert(0, str(_HUB))
sys.path.insert(0, str(_HUB / "agentcore"))

from realtime_metrics import compute_realtime  # noqa: E402  (shipped real-time scorer = source of truth)
from evaluation.provenance_faithfulness import score_provenance as canonical_score  # noqa: E402

# Load the skill's bundled script as a module.
_spec = importlib.util.spec_from_file_location("skill_score", _SKILL / "scripts" / "score_provenance.py")
skill_score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(skill_score)

# The workflow skill (oncology-semantic-hub-analysis) ships an identical co-located copy so Quick's
# Code Execution can run it from that skill's own root. Load it too and drift-guard it.
_WF = _REPO / "skills" / "oncology-semantic-hub-analysis" / "scripts" / "score_provenance.py"
_wf_spec = importlib.util.spec_from_file_location("wf_score", _WF)
wf_score = importlib.util.module_from_spec(_wf_spec)
_wf_spec.loader.exec_module(wf_score)

SAMPLES = [
    ("quick", "144 genes [Graph]; 82 patients [Lake:tcga_mutations]; glioblastoma [OLS:MONDO:0018177]"),
    ("quick", "EGFR drives GBM [Model knowledge]; ~500 genes [Model knowledge]"),
    ("L2", "EGFR targets erlotinib [Graph]; 79 patients [Lake:tcga_mutations]"),   # fabricated graph in L2
    ("L0", "148 patients [Lake:tcga_mutations]"),                                   # fabricated lake in L0
    ("L3", "evidence [KB PMID:21639808]; 82 patients [Lake:tcga_mutations]; EGFR druggable [Graph]"),
    ("L0-web", "per the label [Web:https://x]; EGFR is a driver [Model knowledge]"),
    ("quick", "30 co-occur [Lake:tcga_mutations]; Fisher p=0.28 [Compute]; OR=1.36 [Compute]"),  # computed stat valid in quick
    ("L3", "Fisher p=0.28 [Compute]"),   # L3 has no code tool -> [Compute] is fabricated
    ("quick", "BRAF V600E confers resistance"),                                     # untagged -> unauditable
]


class TestParity(unittest.TestCase):
    def test_skill_script_matches_compute_realtime(self):
        for layer, ans in SAMPLES:
            live = compute_realtime(ans, layer)
            skill = skill_score.score_provenance(ans, layer)
            with self.subTest(layer=layer, ans=ans[:40]):
                self.assertEqual(skill["provenance_faithfulness"], live["provenance_faithfulness"])
                self.assertEqual(skill["grounding_rate"], live["grounding_rate"])
                self.assertEqual(skill["n_tags"], live["n_tags"])
                self.assertEqual(sorted(skill["fabricated"]), sorted(live["fabricated"]))

    def test_valid_inventories_match(self):
        # The skill ships the CONSUMER-facing inventories (L0/L0-web/L1/L2/L3/quick) and intentionally
        # omits benchmark-only ablation cells (L3a/L3b/L3_no_*). For every inventory the skill DOES
        # define, its value must equal the canonical scorer's (no drift on shared keys).
        from evaluation.provenance_faithfulness import VALID as CANON
        for layer, tags in skill_score.VALID.items():
            with self.subTest(layer=layer):
                self.assertIn(layer, CANON)
                self.assertEqual(tags, CANON[layer])
        # the demo/consumer inventory must be present
        self.assertIn("quick", skill_score.VALID)

    def test_workflow_skill_copy_matches(self):
        # oncology-semantic-hub-analysis ships an identical co-located copy (for Quick Code Execution);
        # it must not drift from the eval skill / canonical scorer.
        for layer, ans in SAMPLES:
            live = compute_realtime(ans, layer)
            wf = wf_score.score_provenance(ans, layer)
            with self.subTest(layer=layer, ans=ans[:40]):
                self.assertEqual(wf["provenance_faithfulness"], live["provenance_faithfulness"])
                self.assertEqual(wf["grounding_rate"], live["grounding_rate"])
                self.assertEqual(wf["n_tags"], live["n_tags"])
                self.assertEqual(sorted(wf["fabricated"]), sorted(live["fabricated"]))
        self.assertEqual(wf_score.VALID, skill_score.VALID)

    def test_copies_match_canonical_scorer(self):
        # Directly compare BOTH bundled script copies to the canonical scorer (not just compute_realtime),
        # across all keys incl the untagged/None contract — this is the drift the earlier test missed.
        for layer, ans in SAMPLES:
            canon = canonical_score(ans, layer)
            for name, mod in (("eval-skill", skill_score), ("workflow-skill", wf_score)):
                r = mod.score_provenance(ans, layer)
                with self.subTest(copy=name, layer=layer, ans=ans[:40]):
                    self.assertEqual(r["provenance_faithfulness"], canon["provenance_faithfulness"])
                    self.assertEqual(r["grounding_rate"], canon["grounding_rate"])
                    self.assertEqual(r["n_tags"], canon["n_tags"])
                    self.assertEqual(sorted(r["fabricated"]), sorted(canon["fabricated"]))

    def test_workflow_skill_md_snippet_matches(self):
        # The inline Run-Python snippet embedded in oncology-semantic-hub-analysis/SKILL.md is what Quick
        # actually executes; extract it and verify score() matches the canonical scorer (quick inventory).
        import contextlib
        import io
        import re as _re
        md = (_REPO / "skills" / "oncology-semantic-hub-analysis" / "SKILL.md").read_text()
        block = _re.search(r"```python\n(.*?)```", md, _re.DOTALL).group(1)
        ns = {}
        with contextlib.redirect_stdout(io.StringIO()):   # the snippet prints a demo line on exec
            exec(block, ns)
        for layer, ans in SAMPLES:
            if layer != "quick":   # the SKILL.md snippet hardcodes the `quick` inventory
                continue
            live = compute_realtime(ans, "quick")
            snip = ns["score"](ans, "quick")
            with self.subTest(ans=ans[:40]):
                self.assertEqual(snip["provenance_faithfulness"], live["provenance_faithfulness"])
                self.assertEqual(snip["grounding_rate"], live["grounding_rate"])
                self.assertEqual(snip["n_tags"], live["n_tags"])
                self.assertEqual(sorted(snip.get("fabricated", [])), sorted(live["fabricated"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
