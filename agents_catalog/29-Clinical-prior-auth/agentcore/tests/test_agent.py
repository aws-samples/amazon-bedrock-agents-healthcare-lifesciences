"""Tests for Clinical Prior Auth agent.

All tests are fully automated — no manual steps required.
Run: pytest tests/ -m "not integration"
Run with AWS: AWS_PROFILE=your-profile pytest tests/ -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBillingData:
    """Test billing data loading and specialty lookup."""

    def test_billing_data_loads(self):
        from agent.agent_config.agent import _load_billing_data

        data = _load_billing_data()
        assert "categories" in data
        assert len(data["categories"]) > 0

    def test_billing_data_has_multiple_specialties(self):
        from agent.agent_config.agent import _load_billing_data

        data = _load_billing_data()
        assert len(data["categories"]) >= 3

    def test_each_specialty_has_items(self):
        from agent.agent_config.agent import _load_billing_data

        data = _load_billing_data()
        for name, category in data["categories"].items():
            assert "items" in category, f"Specialty '{name}' missing 'items'"


class TestTools:
    """Test agent tools return expected formats."""

    def test_valid_specialty_returns_documents(self):
        from agent.agent_config.agent import _load_billing_data, get_guidance_document_list

        data = _load_billing_data()
        first_specialty = list(data["categories"].keys())[0]
        result = get_guidance_document_list(speciality=first_specialty)
        assert "not found" not in result.lower()
        assert len(result) > 10

    def test_invalid_specialty_returns_available_list(self):
        from agent.agent_config.agent import get_guidance_document_list

        result = get_guidance_document_list(speciality="nonexistent_xyz")
        assert "not found" in result.lower()
        assert "Available" in result

    def test_parse_pdf_missing_file_returns_error(self):
        from agent.agent_config.agent import parse_pdf

        result = parse_pdf(pdf_file="/nonexistent/file.pdf")
        assert "File not found" in result

    def test_parse_fee_schedule_missing_file(self):
        from agent.agent_config.agent import parse_fee_schedule

        try:
            parse_fee_schedule(fee_schedule_file="/nonexistent/file.xlsx")
        except (FileNotFoundError, ValueError):
            pass  # Expected


class TestModelConfig:
    """Test model configuration is current."""

    def test_primary_model_is_sonnet_4_5(self):
        from agent.agent_config.agent import MODEL_ID

        assert "claude-sonnet-4-5" in MODEL_ID
        assert "20250929" in MODEL_ID

    def test_haiku_model_is_4_5(self):
        from agent.agent_config.agent import HAIKU_MODEL_ID

        assert "claude-haiku-4-5" in HAIKU_MODEL_ID


class TestSystemPrompt:
    """Test system prompt is properly configured."""

    def test_system_prompt_includes_specialties(self):
        from agent.agent_config.agent import _load_billing_data, SYSTEM_PROMPT_TEMPLATE

        data = _load_billing_data()
        specialties = list(data["categories"].keys())
        prompt = SYSTEM_PROMPT_TEMPLATE.format("\n".join(specialties))
        for specialty in specialties[:3]:
            assert specialty in prompt


@pytest.mark.integration
class TestLiveInvocation:
    """Integration tests requiring AWS credentials."""

    def test_sonnet_model_responds(self):
        from strands import Agent
        from strands.models import BedrockModel
        from agent.agent_config.agent import MODEL_ID

        agent = Agent(model=BedrockModel(model_id=MODEL_ID), system_prompt="Reply: OK", tools=[])
        result = agent("Hello")
        assert result.message is not None

    def test_haiku_model_responds(self):
        import boto3
        from agent.agent_config.agent import HAIKU_MODEL_ID

        client = boto3.client("bedrock-runtime")
        response = client.converse(
            modelId=HAIKU_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": "Reply: OK"}]}],
            inferenceConfig={"maxTokens": 10, "temperature": 0},
        )
        assert len(response["output"]["message"]["content"][0]["text"]) > 0

    def test_agent_with_tools_processes_query(self):
        """Full agent with tools can use get_guidance_document_list."""
        from strands import Agent
        from strands.models import BedrockModel
        from agent.agent_config.agent import MODEL_ID, get_guidance_document_list

        agent = Agent(
            model=BedrockModel(model_id=MODEL_ID),
            system_prompt="You help with prior auth. Use tools when asked about specialties.",
            tools=[get_guidance_document_list],
        )
        result = agent("What specialties are available for billing?")
        assert result.message is not None
