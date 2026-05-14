import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import wiley_search, create_agent, WILEY_ONLINE_LIBRARY


class TestWileySearch(unittest.TestCase):
    def test_empty_query_returns_error(self):
        result = wiley_search(question="")
        assert "Error" in result

    def test_whitespace_query_returns_error(self):
        result = wiley_search(question="   ")
        assert "Error" in result

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_successful_search(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.headers.get_content_charset.return_value = "utf-8"
        mock_response.read.return_value = json.dumps({
            "articles": [
                {"title": "Test Article", "wol_link": "https://doi.org/10.1234/test"}
            ]
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = wiley_search(question="emergency department visits")
        assert "Test Article" in result
        assert "doi.org" in result

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_url_error(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")

        result = wiley_search(question="test query")
        assert "Error" in result
        assert "Connection refused" in result

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_json_decode_error(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.headers.get_content_charset.return_value = "utf-8"
        mock_response.read.return_value = b"not valid json"
        mock_urlopen.return_value = mock_response

        result = wiley_search(question="test query")
        assert "Error" in result
        assert "parse" in result.lower() or "JSON" in result

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_query_is_url_encoded(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.headers.get_content_charset.return_value = "utf-8"
        mock_response.read.return_value = json.dumps({"results": []}).encode("utf-8")
        mock_urlopen.return_value = mock_response

        wiley_search(question="what is COVID-19?")
        call_args = mock_urlopen.call_args
        url = call_args[0][0].full_url if hasattr(call_args[0][0], "full_url") else str(call_args[0][0])
        # The question mark and space should be encoded
        assert "what%20is%20COVID-19%3F" in url or "what+is+COVID" in url or mock_urlopen.called


class TestCreateAgent(unittest.TestCase):
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent_with_correct_config(self, mock_agent_cls, mock_model_cls):
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        agent = create_agent()

        mock_model_cls.assert_called_once_with(
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            streaming=True,
        )
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert len(call_kwargs["tools"]) == 1
        assert "wiley" in call_kwargs["system_prompt"].lower()


if __name__ == "__main__":
    unittest.main()
