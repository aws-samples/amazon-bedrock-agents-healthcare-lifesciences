"""Unit tests for the Clinical Study Research Agent."""

import json
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    SYSTEM_PROMPT,
    _parse_data_string,
    create_agent,
    create_pie_chart,
    get_approved_drugs,
    get_trial_details,
    search_trials,
)


class TestSearchTrials:
    @patch("agent.agent_config.agent.requests.get")
    def test_basic_search(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT00001234",
                            "briefTitle": "Test Study",
                        }
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        result = search_trials(
            condition="diabetes",
            intervention="metformin",
            outcome="HbA1c",
            comparison="placebo",
        )
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["protocolSection"]["identificationModule"]["nctId"] == "NCT00001234"

    @patch("agent.agent_config.agent.requests.get")
    def test_search_with_optional_params(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"studies": []}
        mock_get.return_value = mock_response

        result = search_trials(
            condition="asthma",
            intervention="inhaler",
            outcome="FEV1",
            comparison="placebo",
            sponsor="NIH",
            location="United States",
        )

        call_params = mock_get.call_args[1]["params"]
        assert call_params["query.cond"] == "asthma"
        assert call_params["query.spons"] == "NIH"
        assert call_params["query.locn"] == "United States"

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


class TestGetTrialDetails:
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


class TestGetApprovedDrugs:
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
        assert "DrugA" in parsed["drug_names"]
        assert "DrugB" in parsed["drug_names"]

    @patch("agent.agent_config.agent.requests.get")
    def test_query_with_route(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        get_approved_drugs(condition="diabetes", route="nasal")

        call_params = mock_get.call_args[1]["params"]
        assert "route:nasal" in call_params["search"]

    @patch("agent.agent_config.agent.requests.get")
    def test_api_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_get.return_value = mock_response

        result = get_approved_drugs(condition="diabetes")
        parsed = json.loads(result)
        assert "error" in parsed


class TestCreatePieChart:
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
        mock_s3.upload_file.assert_called_once()

    def test_missing_bucket_env(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CHART_IMAGE_BUCKET", None)
            result = create_pie_chart(title="Test", data='[{"label":"A","value":1}]')
            parsed = json.loads(result)
            assert "error" in parsed


class TestParseDataString:
    def test_valid_json(self):
        data = '[{"label": "A", "value": 10}, {"label": "B", "value": 20}]'
        result = _parse_data_string(data)
        assert len(result) == 2
        assert result[0]["label"] == "A"
        assert result[0]["value"] == 10

    def test_non_json_format(self):
        data = "[{label=Phase1, value=30}, {label=Phase2, value=70}]"
        result = _parse_data_string(data)
        assert len(result) == 2
        assert result[0]["label"] == "Phase1"
        assert result[0]["value"] == 30.0


class TestCreateAgent:
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent_with_correct_config(self, mock_agent_cls, mock_model_cls):
        mock_model = Mock()
        mock_model_cls.return_value = mock_model

        create_agent()

        mock_model_cls.assert_called_once_with(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")
        mock_agent_cls.assert_called_once_with(
            model=mock_model,
            system_prompt=SYSTEM_PROMPT,
            tools=[search_trials, get_trial_details, get_approved_drugs, create_pie_chart],
        )


class TestBedrockAgentCoreApp:
    def test_app_initialization(self):
        with patch("agent.agent_config.agent.BedrockModel"), patch(
            "agent.agent_config.agent.Agent"
        ):
            from main import app

            assert app is not None
            assert hasattr(app, "entrypoint")
