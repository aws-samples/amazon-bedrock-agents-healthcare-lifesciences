"""Tests for Clinical Prior Auth AgentCore agent."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.prior_auth_tools import (
    get_guidance_document_list,
    load_billing_data,
    parse_pdf,
)


class TestBillingData:
    """Test billing data loading and specialty lookup."""

    def test_load_billing_data(self):
        """Billing data loads and has categories."""
        data = load_billing_data()
        assert "categories" in data
        assert len(data["categories"]) > 0

    def test_get_guidance_document_list_valid_specialty(self):
        """Valid specialty returns document list."""
        data = load_billing_data()
        first_specialty = list(data["categories"].keys())[0]
        result = get_guidance_document_list(speciality=first_specialty)
        assert "not found" not in result.lower()

    def test_get_guidance_document_list_invalid_specialty(self):
        """Invalid specialty returns available list."""
        result = get_guidance_document_list(speciality="nonexistent_specialty_xyz")
        assert "not found" in result.lower()
        assert "Available" in result


class TestParsePdf:
    """Test PDF parsing tool."""

    def test_parse_pdf_file_not_found(self):
        """Missing file returns error message."""
        result = parse_pdf(pdf_file="/nonexistent/path/file.pdf")
        assert "File not found" in result


class TestAgentCoreApp:
    """Test AgentCore app initialization."""

    @patch("tools.prior_auth_tools.load_billing_data")
    def test_system_prompt_includes_specialties(self, mock_billing):
        """System prompt is built with specialties from billing data."""
        mock_billing.return_value = {
            "categories": {"Cardiology": {"items": []}, "Oncology": {"items": []}}
        }
        from main import SYSTEM_PROMPT_TEMPLATE

        specialties = list(mock_billing.return_value["categories"].keys())
        prompt = SYSTEM_PROMPT_TEMPLATE.format("\n".join(specialties))
        assert "Cardiology" in prompt
        assert "Oncology" in prompt


class TestModelLoad:
    """Test model configuration."""

    def test_model_id_is_current(self):
        """Model ID uses the current Claude Sonnet 4.5."""
        from model.load import MODEL_ID

        assert "claude-sonnet-4-5" in MODEL_ID
        assert "20250929" in MODEL_ID


@pytest.mark.integration
class TestLiveInvocation:
    """Integration tests that require AWS credentials and Bedrock access.

    Run with: pytest -m integration
    """

    def test_model_responds(self):
        """Claude Sonnet 4.5 responds via Bedrock."""
        from model.load import load_model

        model = load_model()
        # Simple invocation to verify model access
        from strands import Agent

        agent = Agent(
            model=model,
            system_prompt="You are a test assistant. Reply with exactly: AGENT_OK",
            tools=[],
        )
        result = agent("Say hello")
        assert result.message is not None

    def test_haiku_model_accessible(self):
        """Claude Haiku 4.5 is accessible for claim calculation."""
        import boto3

        client = boto3.client("bedrock-runtime")
        response = client.converse(
            modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            messages=[{"role": "user", "content": [{"text": "Reply with: OK"}]}],
            inferenceConfig={"maxTokens": 10, "temperature": 0},
        )
        text = response["output"]["message"]["content"][0]["text"]
        assert len(text) > 0
