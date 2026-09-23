"""Unit tests for the Radiology Report Validator Agent."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config import agent as agent_module
from agent.agent_config.agent import (
    SYSTEM_PROMPT,
    create_agent,
    download_guidance_document,
    run_validator,
)


class TestDownloadGuidanceDocument(unittest.TestCase):
    @patch("agent.agent_config.agent._get_s3_client")
    def test_stages_matching_pdf(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "Chest/ACR_Chest.pdf"},
                {"Key": "Chest/NormalChest.pdf"},
                {"Key": "Abdomen/ACR_Abdomen.pdf"},
                {"Key": "Chest/notes.txt"},
            ]
        }
        mock_get_client.return_value = mock_s3

        with patch("os.makedirs"):
            result = download_guidance_document(anatomical_structure="chest")

        assert "ACR_Chest.pdf" in result
        assert "NormalChest.pdf" in result
        assert "ACR_Abdomen.pdf" not in result  # different structure
        assert "notes.txt" not in result  # not a pdf
        assert mock_s3.download_file.call_count == 2

    @patch("agent.agent_config.agent._get_s3_client")
    def test_no_match_returns_message(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": "Abdomen/ACR_Abdomen.pdf"}]}
        mock_get_client.return_value = mock_s3

        with patch("os.makedirs"):
            result = download_guidance_document(anatomical_structure="Chest")

        assert "No ACR guidance document found" in result
        mock_s3.download_file.assert_not_called()

    def test_empty_structure_returns_error(self):
        result = download_guidance_document(anatomical_structure="   ")
        assert "Error" in result

    @patch("agent.agent_config.agent._get_s3_client")
    def test_list_error_returns_message(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.side_effect = Exception("AccessDenied")
        mock_get_client.return_value = mock_s3

        with patch("os.makedirs"):
            result = download_guidance_document(anatomical_structure="Chest")

        assert "Error listing guidance bucket" in result


class TestRunValidator(unittest.TestCase):
    def test_empty_report_returns_error(self):
        result = run_validator(report="")
        assert "Error" in result

    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", return_value=[])
    def test_no_staged_document_returns_message(self, _mock_listdir, _mock_isdir):
        result = run_validator(report="Findings: clear lungs.")
        assert "No ACR guidance document staged" in result

    @patch("agent.agent_config.agent.boto3.client")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data=b"%PDF-1.4 fake")
    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", return_value=["ACR_Chest.pdf"])
    def test_successful_validation(self, _mock_listdir, _mock_isdir, _mock_open, mock_boto):
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "Missing impression section."}]}}
        }
        mock_boto.return_value = mock_client

        result = run_validator(report="Findings: clear lungs.")

        assert result == "Missing impression section."
        # Verify the guideline PDF was attached and inference config passed through.
        _, kwargs = mock_client.converse.call_args
        assert kwargs["modelId"] == agent_module.MODEL_ID
        content = kwargs["messages"][0]["content"]
        assert content[0]["document"]["format"] == "pdf"
        assert kwargs["inferenceConfig"]["maxTokens"] == 2000

    @patch("agent.agent_config.agent.boto3.client")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data=b"%PDF-1.4 fake")
    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", return_value=["ACR_Chest.pdf"])
    def test_skips_non_text_content_block(self, _mock_listdir, _mock_isdir, _mock_open, mock_boto):
        # Sonnet 5 may emit a reasoning block before the text block.
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {
                "message": {
                    "content": [
                        {"reasoningContent": {"reasoningText": {"text": "thinking"}}},
                        {"text": "Add an impression section."},
                    ]
                }
            }
        }
        mock_boto.return_value = mock_client

        result = run_validator(report="Findings: clear lungs.")
        assert result == "Add an impression section."

    @patch("agent.agent_config.agent.boto3.client")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data=b"%PDF-1.4 fake")
    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", return_value=["ACR_Chest.pdf"])
    def test_converse_error_returns_message(self, _mock_listdir, _mock_isdir, _mock_open, mock_boto):
        mock_client = MagicMock()
        mock_client.converse.side_effect = Exception("Throttled")
        mock_boto.return_value = mock_client

        result = run_validator(report="Findings: clear lungs.")
        assert "Error validating report" in result


class TestCreateAgent(unittest.TestCase):
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent_with_correct_config(self, mock_agent_cls, mock_model_cls):
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        create_agent()

        mock_model_cls.assert_called_once_with(
            model_id=agent_module.MODEL_ID,
            streaming=True,
        )
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["system_prompt"] == SYSTEM_PROMPT
        assert len(call_kwargs["tools"]) == 2

    def test_system_prompt_mentions_acr(self):
        assert "acr" in SYSTEM_PROMPT.lower()
        assert "radiology report validator" in SYSTEM_PROMPT.lower()


if __name__ == "__main__":
    unittest.main()
