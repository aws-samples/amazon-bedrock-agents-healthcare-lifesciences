import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    analyze_adverse_events,
    assess_evidence,
    generate_report,
    create_agent,
    _calculate_prr,
    _calculate_confidence_interval,
    _detect_signals,
    _analyze_trends,
    _assess_causality,
)

SAMPLE_OPENFDA_RESULTS = {
    "results": [
        {
            "receivedate": "20250101",
            "serious": "1",
            "patient": {
                "reaction": [
                    {"reactionmeddrapt": "Nausea"},
                    {"reactionmeddrapt": "Headache"},
                ]
            },
        },
        {
            "receivedate": "20250115",
            "serious": "0",
            "patient": {
                "reaction": [
                    {"reactionmeddrapt": "Nausea"},
                ]
            },
        },
        {
            "receivedate": "20250201",
            "serious": "1",
            "patient": {
                "reaction": [
                    {"reactionmeddrapt": "Rash"},
                    {"reactionmeddrapt": "Nausea"},
                ]
            },
        },
    ],
    "total_available": 3,
}


class TestCalculatePRR(unittest.TestCase):
    def test_basic_prr(self):
        result = _calculate_prr(10, 100, 1000, 100000)
        self.assertAlmostEqual(result, 10.0)

    def test_zero_a_returns_none(self):
        self.assertIsNone(_calculate_prr(0, 100, 1000, 100000))

    def test_zero_b_returns_none(self):
        self.assertIsNone(_calculate_prr(10, 0, 1000, 100000))

    def test_zero_denominator_returns_none(self):
        self.assertIsNone(_calculate_prr(10, 100, 0, 0))


class TestConfidenceInterval(unittest.TestCase):
    def test_basic_ci(self):
        ci = _calculate_confidence_interval(50, 100)
        self.assertIsNotNone(ci)
        self.assertLess(ci["lower"], 0.5)
        self.assertGreater(ci["upper"], 0.5)

    def test_zero_total(self):
        self.assertIsNone(_calculate_confidence_interval(10, 0))


class TestAnalyzeTrends(unittest.TestCase):
    def test_counts_reports_by_date(self):
        trends = _analyze_trends(SAMPLE_OPENFDA_RESULTS)
        self.assertEqual(trends["daily_counts"]["2025-01-01"]["total"], 1)
        self.assertEqual(trends["daily_counts"]["2025-01-01"]["serious"], 1)
        self.assertEqual(trends["daily_counts"]["2025-01-15"]["serious"], 0)
        self.assertEqual(len(trends["monthly_counts"]), 2)


class TestDetectSignals(unittest.TestCase):
    def test_detects_signals_above_threshold(self):
        signals = _detect_signals(SAMPLE_OPENFDA_RESULTS, threshold=2.0)
        self.assertGreater(len(signals), 0)
        for sig in signals:
            self.assertGreaterEqual(sig["prr"], 2.0)

    def test_empty_results(self):
        signals = _detect_signals({"results": []})
        self.assertEqual(signals, [])

    def test_signals_sorted_by_prr(self):
        signals = _detect_signals(SAMPLE_OPENFDA_RESULTS, threshold=0.0)
        prrs = [s["prr"] for s in signals]
        self.assertEqual(prrs, sorted(prrs, reverse=True))


class TestAssessCausality(unittest.TestCase):
    def test_strong_with_boxed_warning(self):
        result = _assess_causality([], {"boxed_warnings": ["warning"]})
        self.assertEqual(result["evidence_level"], "Strong")
        self.assertEqual(result["causality_score"], 3)

    def test_moderate_with_warnings(self):
        result = _assess_causality([], {"warnings": ["w"], "boxed_warnings": []})
        self.assertEqual(result["evidence_level"], "Moderate")

    def test_literature_boosts_score(self):
        articles = [{"title": f"Article {i}"} for i in range(5)]
        result = _assess_causality(articles, None)
        self.assertGreaterEqual(result["causality_score"], 2)

    def test_insufficient_with_no_evidence(self):
        result = _assess_causality([], None)
        self.assertEqual(result["evidence_level"], "Insufficient")
        self.assertEqual(result["causality_score"], 0)


class TestAnalyzeAdverseEvents(unittest.TestCase):
    @patch("agent.agent_config.agent._query_openfda")
    def test_returns_results(self, mock_query):
        mock_query.return_value = SAMPLE_OPENFDA_RESULTS
        result = analyze_adverse_events(product_name="Aspirin", time_period=6)
        self.assertIn("Aspirin", result)
        self.assertIn("Total Reports: 3", result)

    @patch("agent.agent_config.agent._query_openfda")
    def test_no_results(self, mock_query):
        mock_query.return_value = {"results": [], "total_available": 0}
        result = analyze_adverse_events(product_name="FakeDrug")
        self.assertIn("No adverse event reports found", result)


class TestAssessEvidence(unittest.TestCase):
    @patch("agent.agent_config.agent._query_fda_label")
    @patch("agent.agent_config.agent._search_pubmed")
    def test_returns_assessment(self, mock_pubmed, mock_label):
        mock_pubmed.return_value = [{"title": "Test Article", "year": "2024", "pmid": "123", "abstract": "text"}]
        mock_label.return_value = {"warnings": ["Some warning"], "adverse_reactions": [], "boxed_warnings": [], "contraindications": []}
        result = assess_evidence(product_name="Aspirin", adverse_event="Nausea")
        self.assertIn("Aspirin", result)
        self.assertIn("Nausea", result)
        self.assertIn("Test Article", result)


class TestGenerateReport(unittest.TestCase):
    def test_generates_report_text(self):
        analysis = json.dumps({
            "product_name": "Aspirin",
            "analysis_period": {"start": "2024-10-28", "end": "2025-04-28"},
            "total_reports": 100,
            "signals": [{"event": "Nausea", "prr": 3.5, "count": 20, "confidence_interval": {"lower": 0.1, "upper": 0.3}}],
            "trends": {"daily_counts": {}},
        })
        evidence = json.dumps({"literature": [], "causality_assessment": {"evidence_level": "Moderate", "causality_score": 2}})
        result = generate_report(analysis_results=analysis, evidence_data=evidence)
        self.assertIn("Safety Signal Detection Report", result)
        self.assertIn("Aspirin", result)
        self.assertIn("Nausea", result)

    def test_handles_invalid_json(self):
        result = generate_report(analysis_results="bad json", evidence_data="bad json")
        self.assertIn("Safety Signal Detection Report", result)


class TestCreateAgent(unittest.TestCase):
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent(self, mock_agent_cls, mock_model_cls):
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()
        agent = create_agent()
        mock_model_cls.assert_called_once_with(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0", streaming=True)
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        self.assertEqual(len(call_kwargs["tools"]), 3)
        self.assertIn("pharmacovigilance", call_kwargs["system_prompt"].lower())


if __name__ == "__main__":
    unittest.main()
