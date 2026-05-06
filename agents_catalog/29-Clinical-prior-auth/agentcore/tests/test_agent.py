"""Tests for Clinical Prior Auth agent."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAgentConfig:
    """Test agent configuration and tools."""

    def test_billing_data_loads(self):
        from agent.agent_config.agent import _load_billing_data

        data = _load_billing_data()
        assert "categories" in data
        assert len(data["categories"]) > 0

    def test_get_guidance_document_list_valid(self):
        from agent.agent_config.agent import _load_billing_data, get_guidance_document_list

        data = _load_billing_data()
        first_specialty = list(data["categories"].keys())[0]
        result = get_guidance_document_list(speciality=first_specialty)
        assert "not found" not in result.lower()

    def test_get_guidance_document_list_invalid(self):
        from agent.agent_config.agent import get_guidance_document_list

        result = get_guidance_document_list(speciality="nonexistent_xyz")
        assert "not found" in result.lower()
        assert "Available" in result

    def test_parse_pdf_missing_file(self):
        from agent.agent_config.agent import parse_pdf

        result = parse_pdf(pdf_file="/nonexistent/file.pdf")
        assert "File not found" in result

    def test_model_ids(self):
        from agent.agent_config.agent import MODEL_ID, HAIKU_MODEL_ID

        assert "claude-sonnet-4-5" in MODEL_ID
        assert "claude-haiku-4-5" in HAIKU_MODEL_ID


@pytest.mark.integration
class TestLiveInvocation:
    """Integration tests requiring AWS credentials."""

    def test_model_responds(self):
        from strands import Agent
        from strands.models import BedrockModel
        from agent.agent_config.agent import MODEL_ID

        agent = Agent(
            model=BedrockModel(model_id=MODEL_ID),
            system_prompt="Reply with exactly: AGENT_OK",
            tools=[],
        )
        result = agent("Hello")
        assert result.message is not None

    def test_haiku_responds(self):
        import boto3
        from agent.agent_config.agent import HAIKU_MODEL_ID

        client = boto3.client("bedrock-runtime")
        response = client.converse(
            modelId=HAIKU_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": "Reply: OK"}]}],
            inferenceConfig={"maxTokens": 10, "temperature": 0},
        )
        assert len(response["output"]["message"]["content"][0]["text"]) > 0
