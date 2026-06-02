import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import web_search, create_agent, SYSTEM_PROMPT


class TestWebSearch:
    """Unit tests for the web_search tool function."""

    def test_missing_api_key(self):
        """Returns error when TAVILY_API_KEY is not set."""
        with patch("agent.agent_config.agent.TAVILY_API_KEY", ""):
            result = web_search(search_query="test query")
            assert "Error" in result
            assert "TAVILY_API_KEY" in result

    @patch("urllib.request.urlopen")
    def test_successful_search(self, mock_urlopen):
        """Returns results on successful Tavily API call."""
        expected = {"results": [{"title": "Test", "url": "https://example.com"}]}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(expected).encode("utf-8")
        mock_urlopen.return_value = mock_response

        with patch("agent.agent_config.agent.TAVILY_API_KEY", "test-key"):
            result = web_search(search_query="test query")

        data = json.loads(result)
        assert data["results"][0]["title"] == "Test"

    @patch("urllib.request.urlopen")
    def test_search_with_target_website(self, mock_urlopen):
        """Passes target_website as include_domains."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"results": []}'
        mock_urlopen.return_value = mock_response

        with patch("agent.agent_config.agent.TAVILY_API_KEY", "test-key"):
            web_search(search_query="test", target_website="example.com")

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        body = json.loads(request_obj.data.decode("utf-8"))
        assert body["include_domains"] == ["example.com"]

    @patch("urllib.request.urlopen")
    def test_search_with_topic_and_days(self, mock_urlopen):
        """Passes topic and days parameters correctly."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"results": []}'
        mock_urlopen.return_value = mock_response

        with patch("agent.agent_config.agent.TAVILY_API_KEY", "test-key"):
            web_search(search_query="news", topic="news", days=7)

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        body = json.loads(request_obj.data.decode("utf-8"))
        assert body["topic"] == "news"
        assert body["days"] == 7

    @patch("urllib.request.urlopen")
    def test_http_error(self, mock_urlopen):
        """Returns error message on HTTP failure."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=429, msg="Too Many Requests", hdrs={}, fp=None
        )

        with patch("agent.agent_config.agent.TAVILY_API_KEY", "test-key"):
            result = web_search(search_query="test")

        assert "Error" in result
        assert "429" in result


class TestCreateAgent:
    """Unit tests for agent creation."""

    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_create_agent_returns_agent(self, mock_agent_cls, mock_model_cls):
        """create_agent returns a configured Agent instance."""
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent

        result = create_agent()

        assert result == mock_agent
        mock_model_cls.assert_called_once_with(
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            streaming=True,
        )
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["system_prompt"] == SYSTEM_PROMPT
        assert web_search in call_kwargs["tools"]
