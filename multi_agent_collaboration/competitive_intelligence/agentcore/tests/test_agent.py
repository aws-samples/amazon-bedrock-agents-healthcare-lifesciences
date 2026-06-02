"""Unit tests for the Competitive Intelligence Agent."""

import json
import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    SYSTEM_PROMPT,
    create_agent,
    sec_company_financials,
    uspto_search,
    web_search,
    _get_cik,
    _get_uspto_api_key,
)


class TestWebSearch:
    def test_missing_api_key(self):
        with patch.dict(os.environ, {"TAVILY_API_KEY": ""}):
            result = web_search(search_query="test query")
            assert "Error" in result

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_successful_search(self, mock_urlopen):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {"results": [{"title": "Test Article", "url": "https://example.com"}]}
        ).encode("utf-8")
        mock_urlopen.return_value = mock_response

        with patch.dict(os.environ, {"TAVILY_API_KEY": "fake-key"}):
            result = web_search(search_query="Eli Lilly news")

        parsed = json.loads(result)
        assert "results" in parsed

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_http_error(self, mock_urlopen):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=429, msg="Rate Limited", hdrs={}, fp=None
        )

        with patch.dict(os.environ, {"TAVILY_API_KEY": "fake-key"}):
            result = web_search(search_query="test")

        assert "Error" in result


class TestSecCompanyFinancials:
    @patch("agent.agent_config.agent._get_cik")
    def test_company_not_found(self, mock_get_cik):
        mock_get_cik.return_value = None
        result = sec_company_financials(company_name="NonexistentCorp", financial_metric="Revenues")
        parsed = json.loads(result)
        assert "error" in parsed

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    @patch("agent.agent_config.agent._get_cik")
    def test_successful_lookup(self, mock_get_cik, mock_urlopen):
        mock_get_cik.return_value = {"cik_str": "789019", "title": "MICROSOFT CORP"}

        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "entityName": "MICROSOFT CORP",
            "label": "Revenues",
            "description": "Total revenues",
            "units": {
                "USD": [
                    {"end": "2023-06-30", "val": 211915000000, "form": "10-K", "frame": "CY2023"},
                    {"end": "2022-06-30", "val": 198270000000, "form": "10-K", "frame": "CY2022"},
                ]
            },
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = sec_company_financials(company_name="Microsoft", financial_metric="Revenues")
        parsed = json.loads(result)
        assert parsed["entity_name"] == "MICROSOFT CORP"
        assert len(parsed["annual_10k_data"]) == 2

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    @patch("agent.agent_config.agent._get_cik")
    def test_invalid_tag(self, mock_get_cik, mock_urlopen):
        import urllib.error

        mock_get_cik.return_value = {"cik_str": "789019", "title": "MICROSOFT CORP"}
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs={}, fp=None
        )

        result = sec_company_financials(company_name="Microsoft", financial_metric="FakeTag")
        parsed = json.loads(result)
        assert "error" in parsed


class TestUsptoSearch:
    @patch("agent.agent_config.agent._get_uspto_api_key", return_value="fake-key")
    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_basic_search(self, mock_urlopen, mock_key):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {"results": [{"applicationNumberText": "17/123456"}], "recordTotalQuantity": 1}
        ).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = uspto_search(search_query="tirzepatide")
        parsed = json.loads(result)
        assert "results" in parsed

    @patch("agent.agent_config.agent._get_uspto_api_key", return_value="fake-key")
    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_search_with_days(self, mock_urlopen, mock_key):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"results": []}).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = uspto_search(search_query="GLP-1 receptor", days="200")

        call_args = mock_urlopen.call_args[0][0]
        body = json.loads(call_args.data.decode("utf-8"))
        assert "rangeFilters" in body

    @patch("agent.agent_config.agent._get_uspto_api_key", return_value="fake-key")
    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_http_error(self, mock_urlopen, mock_key):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs={}, fp=None
        )

        result = uspto_search(search_query="test")
        parsed = json.loads(result)
        assert "error" in parsed


class TestGetUsptoApiKey:
    def test_from_environment(self):
        with patch.dict(os.environ, {"USPTO_API_KEY": "env-key"}):
            assert _get_uspto_api_key() == "env-key"

    @patch("agent.agent_config.agent.boto3.client")
    def test_from_secrets_manager(self, mock_boto_client):
        mock_sm = Mock()
        mock_sm.get_secret_value.return_value = {"SecretString": "sm-key"}
        mock_boto_client.return_value = mock_sm

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("USPTO_API_KEY", None)
            os.environ.pop("USPTO_API_KEY_NAME", None)
            result = _get_uspto_api_key()

        assert result == "sm-key"


class TestCreateAgent:
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent_with_all_tools(self, mock_agent_cls, mock_model_cls):
        mock_model = Mock()
        mock_model_cls.return_value = mock_model

        create_agent()

        mock_model_cls.assert_called_once_with(
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0", streaming=True
        )
        mock_agent_cls.assert_called_once_with(
            model=mock_model,
            system_prompt=SYSTEM_PROMPT,
            tools=[web_search, sec_company_financials, uspto_search],
        )


class TestBedrockAgentCoreApp:
    def test_app_initialization(self):
        with patch("agent.agent_config.agent.BedrockModel"), patch(
            "agent.agent_config.agent.Agent"
        ):
            from main import app

            assert app is not None
            assert hasattr(app, "entrypoint")
