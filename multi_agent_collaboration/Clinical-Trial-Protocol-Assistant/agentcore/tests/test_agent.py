"""Unit tests for the Clinical Trial Protocol Assistant agent."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    ALL_TOOLS,
    SYSTEM_PROMPT,
    _parse_data_string,
    calculate_sample_size,
    create_agent,
    create_pie_chart,
    generate_inclusion_exclusion_criteria,
    get_approved_drugs,
    get_clinical_protocol_template,
    get_trial_details,
    recommend_endpoints,
    search_trials,
)


# ============================================================
# Study Search Tool Tests
# ============================================================


class TestSearchTrials(unittest.TestCase):
    @patch("agent.agent_config.agent.requests.get")
    def test_basic_search(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT00001234"}}}]
        }
        mock_get.return_value = mock_response

        result = search_trials(
            condition="diabetes", intervention="metformin", outcome="HbA1c", comparison="placebo"
        )
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["protocolSection"]["identificationModule"]["nctId"] == "NCT00001234"

    @patch("agent.agent_config.agent.requests.get")
    def test_search_api_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        result = search_trials(
            condition="cancer", intervention="chemo", outcome="survival", comparison="placebo"
        )
        parsed = json.loads(result)
        assert "error" in parsed


class TestGetTrialDetails(unittest.TestCase):
    @patch("agent.agent_config.agent.requests.get")
    def test_get_details(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "protocolSection": {"identificationModule": {"nctId": "NCT12345678"}}
        }
        mock_get.return_value = mock_response

        result = get_trial_details(nctId="NCT12345678")
        parsed = json.loads(result)
        assert parsed["protocolSection"]["identificationModule"]["nctId"] == "NCT12345678"

    @patch("agent.agent_config.agent.requests.get")
    def test_get_details_not_found(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = get_trial_details(nctId="NCT99999999")
        parsed = json.loads(result)
        assert "error" in parsed


class TestGetApprovedDrugs(unittest.TestCase):
    @patch("agent.agent_config.agent.requests.get")
    def test_basic_query(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"products": [{"brand_name": "DrugA", "route": "ORAL"}]},
                {"products": [{"brand_name": "DrugB", "route": "ORAL"}]},
            ]
        }
        mock_get.return_value = mock_response

        result = get_approved_drugs(condition="diabetes")
        parsed = json.loads(result)
        assert parsed["total_drugs"] == 2

    @patch("agent.agent_config.agent.requests.get")
    def test_api_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_get.return_value = mock_response

        result = get_approved_drugs(condition="diabetes")
        parsed = json.loads(result)
        assert "error" in parsed


class TestCreatePieChart(unittest.TestCase):
    @patch("agent.agent_config.agent.boto3.client")
    def test_creates_chart(self, mock_boto_client):
        mock_s3 = Mock()
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/chart.png"
        mock_boto_client.return_value = mock_s3

        data = json.dumps([{"label": "Phase 1", "value": 30}, {"label": "Phase 2", "value": 70}])
        with patch.dict(os.environ, {"CHART_IMAGE_BUCKET": "test-bucket"}):
            result = create_pie_chart(title="Trial Phases", data=data)
        parsed = json.loads(result)
        assert "url" in parsed

    def test_missing_bucket_env(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CHART_IMAGE_BUCKET", None)
            result = create_pie_chart(title="Test", data='[{"label":"A","value":1}]')
            parsed = json.loads(result)
            assert "error" in parsed


# ============================================================
# Protocol Generation Tool Tests
# ============================================================


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
            condition="type 2 diabetes", intervention="GLP-1 agonist",
            population="adults", study_phase="Phase 2",
        )
        data = json.loads(result)
        assert "inclusion" in data
        assert "exclusion" in data
        assert any("HbA1c" in c for c in data["inclusion"])

    def test_cancer_criteria(self):
        result = generate_inclusion_exclusion_criteria(
            condition="breast cancer", intervention="chemotherapy",
            population="adults", study_phase="Phase 3",
        )
        data = json.loads(result)
        assert any("RECIST" in c for c in data["inclusion"])

    def test_generic_condition(self):
        result = generate_inclusion_exclusion_criteria(
            condition="rare genetic disorder", intervention="enzyme replacement",
            population="adults", study_phase="Phase 2",
        )
        data = json.loads(result)
        assert "note" in data

    def test_pediatric_population(self):
        result = generate_inclusion_exclusion_criteria(
            condition="depression", intervention="SSRI",
            population="pediatric", study_phase="Phase 2",
        )
        data = json.loads(result)
        assert any("2-17" in c for c in data["inclusion"])


class TestRecommendEndpoints(unittest.TestCase):
    def test_diabetes_phase2(self):
        result = recommend_endpoints(
            condition="type 2 diabetes", intervention="GLP-1 agonist", study_phase="Phase 2"
        )
        data = json.loads(result)
        assert "primary" in data
        assert any("HbA1c" in e for e in data["primary"])

    def test_generic_condition(self):
        result = recommend_endpoints(
            condition="rare disease", intervention="new drug", study_phase="Phase 2"
        )
        data = json.loads(result)
        assert "note" in data

    def test_biologic_adds_exploratory(self):
        result = recommend_endpoints(
            condition="type 2 diabetes", intervention="monoclonal antibody", study_phase="Phase 2"
        )
        data = json.loads(result)
        assert any("Immunogenicity" in e for e in data.get("exploratory", []))


class TestCalculateSampleSize(unittest.TestCase):
    def test_continuous_endpoint(self):
        result = calculate_sample_size(
            study_design="superiority", power="80%", effect_size="0.5", endpoint_type="continuous"
        )
        data = json.loads(result)
        assert data["sample_size_per_group"] > 0
        assert data["total_sample_size"] == data["sample_size_per_group"] * 2
        assert data["recommended_sample_size"] > data["total_sample_size"]

    def test_non_inferiority_increases_size(self):
        sup = json.loads(calculate_sample_size(
            study_design="superiority", power="80%", effect_size="0.5", endpoint_type="continuous"
        ))
        ni = json.loads(calculate_sample_size(
            study_design="non-inferiority", power="80%", effect_size="0.5", endpoint_type="continuous"
        ))
        assert ni["sample_size_per_group"] > sup["sample_size_per_group"]


# ============================================================
# Helper Tests
# ============================================================


class TestParseDataString(unittest.TestCase):
    def test_valid_json(self):
        data = '[{"label": "A", "value": 10}, {"label": "B", "value": 20}]'
        result = _parse_data_string(data)
        assert len(result) == 2
        assert result[0]["value"] == 10

    def test_non_json_format(self):
        data = "[{label=Phase1, value=30}, {label=Phase2, value=70}]"
        result = _parse_data_string(data)
        assert len(result) == 2
        assert result[0]["value"] == 30.0


# ============================================================
# Agent Creation Test
# ============================================================


class TestCreateAgent(unittest.TestCase):
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent_with_all_tools(self, mock_agent_cls, mock_model_cls):
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()
        agent = create_agent()
        mock_model_cls.assert_called_once_with(
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            streaming=True,
        )
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert len(call_kwargs["tools"]) == 8
        assert call_kwargs["tools"] == ALL_TOOLS


if __name__ == "__main__":
    unittest.main()
