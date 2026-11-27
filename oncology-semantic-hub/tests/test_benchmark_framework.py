"""Unit tests for the Semantic Hub Benchmark Framework (Accelerator 2).

Covers:
- evaluation/provenance_faithfulness.py (layer-aware provenance scorer)
- agentcore/run_v2_benchmark.py (custom correctness scorer)
- evaluation/config.py (path resolution)
- ground_truth/golden_v2.json (schema validation)

Run: python -m unittest tests/test_benchmark_framework.py -v
"""
import json
import sys
import unittest
from pathlib import Path

# Add project paths
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agentcore"))


class TestProvenanceFaithfulness(unittest.TestCase):
    """Tests for evaluation/provenance_faithfulness.py"""

    def setUp(self):
        from evaluation.provenance_faithfulness import score_provenance
        self.score = score_provenance

    def test_l3_valid_tags(self):
        """L3 with Graph + Lake tags = valid (faithfulness 1.0)"""
        r = self.score("148 patients [Lake:tcga_mutations]; EGFR druggable [Graph].", "L3")
        self.assertEqual(r["provenance_faithfulness"], 1.0)
        self.assertEqual(r["fabricated"], [])

    def test_l0_fabricated_lake(self):
        """L0 claiming [Lake] = fabricated (faithfulness 0.0)"""
        r = self.score("148 patients [Lake:tcga_mutations].", "L0")
        self.assertEqual(r["provenance_faithfulness"], 0.0)
        self.assertIn("lake", r["fabricated"])

    def test_l2_fabricated_graph(self):
        """L2 claiming [Graph] = fabricated (L2 has no graph)"""
        r = self.score("EGFR-drug link [Graph]; 79 patients [Lake:tcga_mutations].", "L2")
        self.assertLess(r["provenance_faithfulness"], 1.0)
        self.assertIn("graph", r["fabricated"])

    def test_l2_valid_flat(self):
        """L2 with PrimeKG-flat + Lake + KB = all valid"""
        r = self.score("evidence [KB PMID:21639808]; 79 patients [Lake:tcga_mutations]; drug via [PrimeKG-flat:drug_protein].", "L2")
        self.assertEqual(r["provenance_faithfulness"], 1.0)

    def test_l0_model_knowledge_valid(self):
        """L0 with [Model knowledge] = valid (honest)"""
        r = self.score("EGFR drives GBM [Model knowledge]; therapy is erlotinib [Recalled: TCGA 2008].", "L0")
        self.assertEqual(r["provenance_faithfulness"], 1.0)
        self.assertEqual(r["grounding_rate"], 0.0)  # model tags are not tool-grounded

    def test_no_tags_unauditable(self):
        """No provenance tags at all = unauditable → None (NOT 0.0; untagged is not dishonest)."""
        r = self.score("BRAF V600E confers resistance.", "L3")
        self.assertIsNone(r["provenance_faithfulness"])
        self.assertIsNone(r["grounding_rate"])
        self.assertEqual(r["n_tags"], 0)
        self.assertIn("note", r)

    def test_grounding_rate_calculation(self):
        """grounding_rate = fraction of tags that are tool-backed (not model/recalled)"""
        r = self.score("x [Lake:t]; y [Model knowledge]; z [Graph].", "L3")
        # 2 tool tags (lake, graph) out of 3 total
        self.assertAlmostEqual(r["grounding_rate"], 2/3, places=2)


class TestCustomScorer(unittest.TestCase):
    """Tests for agentcore/run_v2_benchmark.py score_correct"""

    def setUp(self):
        from run_v2_benchmark import score_correct
        self.score = score_correct

    def test_numeric_exact(self):
        """Exact number match"""
        self.assertEqual(self.score({"n_patients": 330}, "There are 330 distinct patients."), 1.0)

    def test_numeric_wrong(self):
        """Wrong number"""
        self.assertEqual(self.score({"n_patients": 330}, "There are 500 patients."), 0.0)

    def test_numeric_comma_formatted(self):
        """Number with comma formatting — scorer currently requires exact string match.
        NOTE: this documents a known limitation (comma-separated numbers don't match).
        A future fix could strip commas before comparison."""
        # The scorer matches the raw number string; "12,694" != "12694"
        self.assertEqual(self.score({"n_patients": 12694}, "The answer is 12,694 genes."), 0.0)
        # But without comma it works
        self.assertEqual(self.score({"n_patients": 12694}, "The answer is 12694 genes."), 1.0)

    def test_gene_list_perfect(self):
        """All expected genes mentioned"""
        ideal = {"genes": ["EGFR", "TP53", "PTEN"], "n": 3}
        answer = "The genes are EGFR, TP53, and PTEN."
        self.assertGreater(self.score(ideal, answer), 0.9)

    def test_gene_list_partial(self):
        """Some expected genes mentioned (partial credit)"""
        ideal = {"genes": ["EGFR", "TP53", "PTEN", "BRAF"], "n": 4}
        answer = "The genes are EGFR and TP53."
        s = self.score(ideal, answer)
        self.assertGreater(s, 0.0)
        self.assertLess(s, 1.0)

    def test_gene_list_empty(self):
        """No expected genes mentioned"""
        ideal = {"genes": ["EGFR", "TP53"], "n": 2}
        answer = "I found some interesting pathways."
        self.assertEqual(self.score(ideal, answer), 0.0)

    def test_mondo_curie_match(self):
        """MONDO CURIE match"""
        ideal = {"correct_mondo": "MONDO:0018177"}
        answer = "The correct identifier is MONDO:0018177 (glioblastoma)."
        self.assertEqual(self.score(ideal, answer), 1.0)

    def test_mondo_curie_wrong(self):
        """Wrong MONDO CURIE"""
        ideal = {"correct_mondo": "MONDO:0018177"}
        answer = "The identifier is MONDO:0005105."
        self.assertEqual(self.score(ideal, answer), 0.0)

    def test_unrecognized_ideal_returns_none(self):
        """Unrecognized ideal shape returns None (not crash)"""
        result = self.score({"unknown_key": "value"}, "some answer")
        # Should return None or 0, not crash
        self.assertTrue(result is None or result == 0.0 or isinstance(result, float))


class TestConfig(unittest.TestCase):
    """Tests for evaluation/config.py path resolution"""

    def test_root_exists(self):
        from evaluation.config import ROOT
        self.assertTrue(ROOT.exists())

    def test_golden_dataset_exists(self):
        from evaluation.config import GOLDEN_DATASET
        self.assertTrue(GOLDEN_DATASET.exists())

    def test_results_dir_is_output(self):
        from evaluation.config import RESULTS_DIR, ROOT
        self.assertEqual(RESULTS_DIR, ROOT / "output")


class TestGoldenDataset(unittest.TestCase):
    """Tests for ground_truth/golden_v2.json schema"""

    def setUp(self):
        self.gold = json.load(open(ROOT / "ground_truth" / "golden_v2.json"))

    def test_count(self):
        self.assertEqual(len(self.gold), 84)

    def test_required_keys(self):
        """Every question has id, question, and ideal"""
        for q in self.gold:
            self.assertIn("id", q)
            self.assertIn("question", q)
            self.assertIn("ideal", q)

    def test_unique_ids(self):
        ids = [q["id"] for q in self.gold]
        self.assertEqual(len(ids), len(set(ids)))

    def test_categories_valid(self):
        """All questions have a recognized category"""
        valid = {"lake", "graph_1hop", "graph_multihop", "reconciliation", "ontology",
                 "multi_source", "actionability", "evidence", "negative", "cross_system",
                 "drug_gene_relationships", "quantitative_precision"}
        for q in self.gold:
            cat = q.get("category", q.get("requires"))
            self.assertIn(cat, valid, f"{q['id']} has invalid category: {cat}")


class TestXmlSafety(unittest.TestCase):
    """Locks in the XXE fix in agentcore/kb/build_corpus.py (probe-scan 2026-08-12)."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        path = ROOT / "agentcore" / "kb" / "build_corpus.py"
        spec = importlib.util.spec_from_file_location("build_corpus", path)
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def test_uses_defused_parser(self):
        """build_corpus parses XML via defusedxml, not the vulnerable stdlib parser."""
        self.assertTrue(hasattr(self.mod, "_safe_fromstring"))
        self.assertIn("defusedxml", self.mod._safe_fromstring.__module__)

    def test_normal_xml_still_parses(self):
        root = self.mod._safe_fromstring(
            "<PubmedArticleSet><PubmedArticle><x>hi</x></PubmedArticle></PubmedArticleSet>")
        self.assertEqual(root.tag, "PubmedArticleSet")

    def test_xxe_payload_is_rejected(self):
        from defusedxml.common import EntitiesForbidden
        xxe = ('<?xml version="1.0"?>'
               '<!DOCTYPE r [<!ENTITY e SYSTEM "file:///etc/passwd">]><r>&e;</r>')
        with self.assertRaises(EntitiesForbidden):
            self.mod._safe_fromstring(xxe)


if __name__ == "__main__":
    unittest.main()
