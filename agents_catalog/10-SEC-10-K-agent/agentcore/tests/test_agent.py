"""Unit tests for the SEC 10-K Search Agent."""

import json
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    SYSTEM_PROMPT,
    _get_cik,
    _get_embedding,
    create_agent,
    find_relevant_tags,
    get_company_concept,
)


class TestGetCik:
    def test_valid_company(self, tmp_path):
        data = {"0": {"cik_str": "1018724", "ticker": "AMZN", "title": "AMAZON COM INC"}}
        f = tmp_path / "cik.json"
        f.write_text(json.dumps(data))

        result = _get_cik("Amazon", f)
        assert result is not None
        assert result["cik_str"] == "1018724"

    def test_no_match(self, tmp_path):
        data = {"0": {"cik_str": "1018724", "ticker": "AMZN", "title": "AMAZON COM INC"}}
        f = tmp_path / "cik.json"
        f.write_text(json.dumps(data))

        result = _get_cik("xyznonexistent", f, score_cutoff=95)
        assert result is None

    def test_missing_file(self, tmp_path):
        result = _get_cik("Amazon", tmp_path / "missing.json")
        assert result is None

    def test_empty_data(self, tmp_path):
        f = tmp_path / "cik.json"
        f.write_text("{}")

        result = _get_cik("Amazon", f)
        assert result is None


class TestGetEmbedding:
    def test_returns_numpy_array(self):
        mock_client = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode()
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = _get_embedding(mock_client, "test text")
        np.testing.assert_array_almost_equal(result, np.array([0.1, 0.2, 0.3]))


class TestFindRelevantTags:
    @patch("agent.agent_config.agent.boto3.client")
    @patch("agent.agent_config.agent.np.load")
    def test_returns_results(self, mock_np_load, mock_boto_client, tmp_path):
        # Set up descriptions file
        desc_file = tmp_path / "descriptions.csv"
        desc_file.write_text(
            "us-gaap,AccountsPayableCurrent,Carrying value of accounts payable\n"
            "us-gaap,Revenue,Total revenue from operations\n"
        )
        embed_file = tmp_path / "embeddings.npy"

        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]])
        mock_np_load.return_value = mock_embeddings

        mock_bedrock = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({"embedding": [0.9, 0.8, 0.7]}).encode()
        mock_bedrock.invoke_model.return_value = {"body": mock_body}
        mock_boto_client.return_value = mock_bedrock

        with patch.dict(os.environ, {"DESCRIPTIONS_PATH": str(desc_file), "EMBEDDINGS_PATH": str(embed_file)}):
            result = find_relevant_tags(query="revenue")

        parsed = json.loads(result)
        assert len(parsed) > 0
        assert "tag" in parsed[0]
        assert "description" in parsed[0]

    @patch("agent.agent_config.agent.boto3.client")
    @patch("agent.agent_config.agent.np.load")
    def test_downloads_files_if_missing(self, mock_np_load, mock_boto_client, tmp_path):
        desc_file = tmp_path / "desc.csv"
        embed_file = tmp_path / "embed.npy"

        # Files don't exist yet - should trigger download
        mock_s3 = MagicMock()
        mock_bedrock = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({"embedding": [0.1, 0.2]}).encode()
        mock_bedrock.invoke_model.return_value = {"body": mock_body}

        def client_factory(service):
            if service == "s3":
                return mock_s3
            return mock_bedrock

        mock_boto_client.side_effect = client_factory
        mock_np_load.return_value = np.array([[0.1, 0.2]])

        # Create the files after "download" by mocking download_file
        def fake_download(bucket, key, path):
            if "descriptions" in key:
                with open(path, "w") as f:
                    f.write("us-gaap,TestTag,Test description\n")

        mock_s3.download_file.side_effect = fake_download

        with patch.dict(os.environ, {"DESCRIPTIONS_PATH": str(desc_file), "EMBEDDINGS_PATH": str(embed_file)}):
            with patch("os.path.exists", return_value=False):
                result = find_relevant_tags(query="test")

        assert mock_s3.download_file.call_count == 2


class TestGetCompanyConcept:
    @patch("agent.agent_config.agent._get_cik")
    @patch("agent.agent_config.agent.EdgarClient")
    def test_successful_lookup(self, mock_edgar_cls, mock_get_cik):
        mock_get_cik.return_value = {"cik_str": "1018724", "ticker": "AMZN", "title": "AMAZON COM INC"}
        mock_edgar = MagicMock()
        mock_edgar.get_company_concept.return_value = {
            "entityName": "AMAZON.COM, INC.",
            "label": "Accounts Payable, Current",
            "units": {
                "USD": [
                    {"end": "2023-12-31", "val": 1000000, "form": "10-K", "frame": "CY2023"},
                    {"end": "2022-12-31", "val": 900000, "form": "10-K", "frame": "CY2022"},
                    {"end": "2023-06-30", "val": 950000, "form": "10-Q"},
                ]
            },
        }
        mock_edgar_cls.return_value = mock_edgar

        result = get_company_concept(company_name="Amazon", tag="AccountsPayableCurrent")
        parsed = json.loads(result)

        assert parsed["entity_name"] == "AMAZON.COM, INC."
        assert parsed["unit"] == "USD"
        assert len(parsed["data"]) == 2  # Only 10-K with frame

    @patch("agent.agent_config.agent._get_cik")
    def test_company_not_found(self, mock_get_cik):
        mock_get_cik.return_value = None

        result = get_company_concept(company_name="NonexistentCorp", tag="Revenue")
        parsed = json.loads(result)

        assert "error" in parsed
        assert "NonexistentCorp" in parsed["error"]

    @patch("agent.agent_config.agent._get_cik")
    @patch("agent.agent_config.agent.EdgarClient")
    def test_edgar_api_error(self, mock_edgar_cls, mock_get_cik):
        mock_get_cik.return_value = {"cik_str": "123", "ticker": "X", "title": "X"}
        mock_edgar = MagicMock()
        mock_edgar.get_company_concept.side_effect = Exception("API timeout")
        mock_edgar_cls.return_value = mock_edgar

        result = get_company_concept(company_name="X", tag="Revenue")
        parsed = json.loads(result)

        assert "error" in parsed


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
            tools=[find_relevant_tags, get_company_concept],
        )


class TestBedrockAgentCoreApp:
    def test_app_initialization(self):
        with patch("agent.agent_config.agent.BedrockModel"), patch("agent.agent_config.agent.Agent"):
            from main import app

            assert app is not None
            assert hasattr(app, "entrypoint")
