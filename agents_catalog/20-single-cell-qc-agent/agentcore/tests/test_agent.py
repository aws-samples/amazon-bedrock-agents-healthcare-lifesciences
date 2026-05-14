import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    analyze_web_summary,
    validate_qc_metrics,
    _parse_s3_uri,
    _get_s3_object,
    create_agent,
)


class TestParseS3Uri(unittest.TestCase):
    def test_valid_uri(self):
        bucket, key = _parse_s3_uri("s3://my-bucket/path/to/file.pdf")
        assert bucket == "my-bucket"
        assert key == "path/to/file.pdf"

    def test_invalid_scheme(self):
        with self.assertRaises(ValueError):
            _parse_s3_uri("https://my-bucket/path/to/file.pdf")

    def test_root_key(self):
        bucket, key = _parse_s3_uri("s3://bucket/file.pdf")
        assert bucket == "bucket"
        assert key == "file.pdf"


class TestGetS3Object(unittest.TestCase):
    @patch("agent.agent_config.agent._get_s3_client")
    def test_successful_get(self, mock_get_client):
        mock_client = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"pdf-content"
        mock_client.get_object.return_value = {"Body": mock_body}
        mock_get_client.return_value = mock_client

        result = _get_s3_object("s3://bucket/file.pdf")
        assert result == b"pdf-content"
        mock_client.get_object.assert_called_once_with(Bucket="bucket", Key="file.pdf")

    @patch("agent.agent_config.agent._get_s3_client")
    def test_invalid_uri_raises(self, mock_get_client):
        with self.assertRaises(ValueError):
            _get_s3_object("http://not-s3/file.pdf")


class TestAnalyzeWebSummary(unittest.TestCase):
    @patch("agent.agent_config.agent._get_bedrock_client")
    @patch("agent.agent_config.agent._get_s3_object")
    def test_successful_analysis(self, mock_s3, mock_bedrock):
        mock_s3.return_value = b"fake-pdf-bytes"
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "QC metrics: all good"}]}}
        }
        mock_bedrock.return_value = mock_client

        result = analyze_web_summary(web_summary_s3_uri="s3://bucket/summary.pdf")
        assert "QC metrics" in result
        mock_s3.assert_called_once_with("s3://bucket/summary.pdf")
        mock_client.converse.assert_called_once()

    @patch("agent.agent_config.agent._get_s3_object")
    def test_s3_error_returns_message(self, mock_s3):
        mock_s3.side_effect = ValueError("Invalid S3 URI: bad-uri")

        result = analyze_web_summary(web_summary_s3_uri="bad-uri")
        assert "Error" in result


class TestValidateQcMetrics(unittest.TestCase):
    @patch("agent.agent_config.agent._get_bedrock_client")
    @patch("agent.agent_config.agent._get_s3_object")
    def test_successful_validation(self, mock_s3, mock_bedrock):
        mock_s3.side_effect = [b"web-summary-bytes", b"tech-doc-bytes"]
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "✅ All metrics pass"}]}}
        }
        mock_bedrock.return_value = mock_client

        result = validate_qc_metrics(
            web_summary_s3_uri="s3://bucket/summary.pdf",
            technical_doc_s3_uri="s3://bucket/tech.pdf",
        )
        assert "✅" in result
        assert mock_s3.call_count == 2

    @patch("agent.agent_config.agent._get_s3_object")
    def test_s3_error_returns_message(self, mock_s3):
        mock_s3.side_effect = Exception("Access denied")

        result = validate_qc_metrics(
            web_summary_s3_uri="s3://bucket/summary.pdf",
            technical_doc_s3_uri="s3://bucket/tech.pdf",
        )
        assert "Error" in result


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
        assert len(call_kwargs["tools"]) == 2
        assert "single cell" in call_kwargs["system_prompt"].lower()


if __name__ == "__main__":
    unittest.main()
