"""Unit tests for the USPTO Patent Search Agent."""

import json
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    SYSTEM_PROMPT,
    _get_api_key,
    create_agent,
    uspto_search,
)


class TestGetApiKey:
    def test_from_environment(self):
        with patch.dict(os.environ, {"USPTO_API_KEY": "test-key-123"}):
            assert _get_api_key() == "test-key-123"

    def test_from_environment_custom_name(self):
        with patch.dict(os.environ, {"USPTO_API_KEY_NAME": "MY_KEY", "MY_KEY": "custom-key"}):
            assert _get_api_key() == "custom-key"

    @patch("agent.agent_config.agent.boto3.client")
    def test_from_secrets_manager(self, mock_boto_client):
        mock_sm = Mock()
        mock_sm.get_secret_value.return_value = {"SecretString": "secret-key"}
        mock_boto_client.return_value = mock_sm

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("USPTO_API_KEY", None)
            os.environ.pop("USPTO_API_KEY_NAME", None)
            result = _get_api_key()

        assert result == "secret-key"
        mock_sm.get_secret_value.assert_called_once_with(SecretId="USPTO_API_KEY")


class TestUsptoSearch:
    @patch("agent.agent_config.agent._get_api_key", return_value="fake-key")
    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_basic_search(self, mock_urlopen, mock_key):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {"results": [{"applicationNumberText": "12345"}], "recordTotalQuantity": 1}
        ).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = uspto_search(search_query="nanobody")
        parsed = json.loads(result)

        assert "results" in parsed
        assert parsed["results"][0]["applicationNumberText"] == "12345"

    @patch("agent.agent_config.agent._get_api_key", return_value="fake-key")
    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_search_with_days(self, mock_urlopen, mock_key):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"results": []}).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = uspto_search(search_query="cancer treatment", days="30")

        # Verify the request was made with rangeFilters
        call_args = mock_urlopen.call_args[0][0]
        body = json.loads(call_args.data.decode("utf-8"))
        assert "rangeFilters" in body
        assert body["rangeFilters"][0]["field"] == "applicationMetaData.effectiveFilingDate"

    @patch("agent.agent_config.agent._get_api_key", return_value="fake-key")
    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_search_http_error(self, mock_urlopen, mock_key):
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs={}, fp=None
        )

        result = uspto_search(search_query="test")
        parsed = json.loads(result)
        assert "error" in parsed


class TestCreateAgent:
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent_with_correct_config(self, mock_agent_cls, mock_model_cls):
        mock_model = Mock()
        mock_model_cls.return_value = mock_model

        create_agent()

        mock_model_cls.assert_called_once_with(
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        )
        mock_agent_cls.assert_called_once_with(
            model=mock_model,
            system_prompt=SYSTEM_PROMPT,
            tools=[uspto_search],
        )


class TestBedrockAgentCoreApp:
    def test_app_initialization(self):
        with patch("agent.agent_config.agent.BedrockModel"), patch(
            "agent.agent_config.agent.Agent"
        ):
            from main import app

            assert app is not None
            assert hasattr(app, "entrypoint")
