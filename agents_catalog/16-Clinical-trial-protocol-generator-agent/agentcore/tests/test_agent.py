import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    get_clinical_protocol_template,
    generate_inclusion_exclusion_criteria,
    recommend_endpoints,
    calculate_sample_size,
    create_agent,
)


class TestGetClinicalProtocolTemplate(unittest.TestCase):
    def test_returns_cdm_content(self):
        result = get_clinical_protocol_template()
        assert "Clinical Document Model" in result
        assert "protocol_id" in result
        assert "study_objectives" in result

    @patch("agent.agent_config.agent.open", side_effect=FileNotFoundError("not found"))
    def test_handles_missing_file(self, mock_open):
        result = get_clinical_protocol_template()
        assert "Error" in result


class TestGenerateInclusionExclusionCriteria(unittest.TestCase):
    def test_diabetes_criteria(self):
        result = generate_inclusion_exclusion_criteria(
            condition="type 2 diabetes",
            intervention="GLP-1 agonist",
            population="adults",
            study_phase="Phase 2",
        )
        data = json.loads(result)
        assert "inclusion" in data
        assert "exclusion" in data
        assert any("HbA1c" in c for c in data["inclusion"])

    def test_cancer_criteria(self):
        result = generate_inclusion_exclusion_criteria(
            condition="breast cancer",
            intervention="chemotherapy",
            population="adults",
            study_phase="Phase 3",
        )
        data = json.loads(result)
        assert any("RECIST" in c for c in data["inclusion"])
        assert any("broader target population" in c for c in data["inclusion"])

    def test_generic_condition(self):
        result = generate_inclusion_exclusion_criteria(
            condition="rare genetic disorder",
            intervention="enzyme replacement",
            population="adults",
            study_phase="Phase 2",
        )
        data = json.loads(result)
        assert "note" in data
        assert any("rare genetic disorder" in c for c in data["inclusion"])

    def test_biologic_adds_exclusions(self):
        result = generate_inclusion_exclusion_criteria(
            condition="type 2 diabetes",
            intervention="monoclonal antibody",
            population="adults",
            study_phase="Phase 2",
        )
        data = json.loads(result)
        assert any("allergic" in c.lower() for c in data["exclusion"])

    def test_pediatric_population(self):
        result = generate_inclusion_exclusion_criteria(
            condition="depression",
            intervention="SSRI",
            population="pediatric",
            study_phase="Phase 2",
        )
        data = json.loads(result)
        assert any("2-17" in c for c in data["inclusion"])

    def test_phase_1_criteria(self):
        result = generate_inclusion_exclusion_criteria(
            condition="type 2 diabetes",
            intervention="new drug",
            population="adults",
            study_phase="Phase 1",
        )
        data = json.loads(result)
        assert any("Healthy volunteers" in c for c in data["inclusion"])


class TestRecommendEndpoints(unittest.TestCase):
    def test_diabetes_phase2(self):
        result = recommend_endpoints(
            condition="type 2 diabetes",
            intervention="GLP-1 agonist",
            study_phase="Phase 2",
        )
        data = json.loads(result)
        assert "primary" in data
        assert "secondary" in data
        assert any("HbA1c" in e for e in data["primary"])

    def test_heart_failure_phase3(self):
        result = recommend_endpoints(
            condition="heart failure",
            intervention="beta blocker",
            study_phase="Phase 3",
        )
        data = json.loads(result)
        assert any("cardiovascular death" in e.lower() for e in data["primary"])

    def test_generic_condition(self):
        result = recommend_endpoints(
            condition="rare disease",
            intervention="new drug",
            study_phase="Phase 2",
        )
        data = json.loads(result)
        assert "note" in data

    def test_biologic_adds_exploratory(self):
        result = recommend_endpoints(
            condition="type 2 diabetes",
            intervention="monoclonal antibody",
            study_phase="Phase 2",
        )
        data = json.loads(result)
        assert any("Immunogenicity" in e for e in data.get("exploratory", []))


class TestCalculateSampleSize(unittest.TestCase):
    def test_continuous_endpoint(self):
        result = calculate_sample_size(
            study_design="superiority",
            power="80%",
            effect_size="0.5",
            endpoint_type="continuous",
        )
        data = json.loads(result)
        assert data["sample_size_per_group"] > 0
        assert data["total_sample_size"] == data["sample_size_per_group"] * 2
        assert data["recommended_sample_size"] > data["total_sample_size"]

    def test_binary_endpoint(self):
        result = calculate_sample_size(
            study_design="superiority",
            power="90%",
            effect_size="15%",
            endpoint_type="binary",
        )
        data = json.loads(result)
        assert data["assumptions"]["power"] == 0.9
        assert data["assumptions"]["alpha"] == 0.05

    def test_non_inferiority_increases_size(self):
        sup = json.loads(calculate_sample_size(
            study_design="superiority", power="80%", effect_size="0.5", endpoint_type="continuous"
        ))
        ni = json.loads(calculate_sample_size(
            study_design="non-inferiority", power="80%", effect_size="0.5", endpoint_type="continuous"
        ))
        assert ni["sample_size_per_group"] > sup["sample_size_per_group"]

    def test_time_to_event(self):
        result = calculate_sample_size(
            study_design="superiority",
            power="80%",
            effect_size="0.3",
            endpoint_type="time-to-event",
        )
        data = json.loads(result)
        assert data["sample_size_per_group"] > 0


class TestCreateAgent(unittest.TestCase):
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent(self, mock_agent_cls, mock_model_cls):
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()
        agent = create_agent()
        mock_model_cls.assert_called_once_with(
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            streaming=True,
        )
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert len(call_kwargs["tools"]) == 4


if __name__ == "__main__":
    unittest.main()
