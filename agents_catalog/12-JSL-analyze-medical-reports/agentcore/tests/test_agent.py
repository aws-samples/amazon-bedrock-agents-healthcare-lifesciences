import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    extract_social_determinants_of_health,
    extract_icd_10_cm_sentence_entities,
    _call_sagemaker_endpoint,
    create_agent,
    SYSTEM_PROMPT,
)


class TestCallSagemakerEndpoint(unittest.TestCase):
    @patch("agent.agent_config.agent._get_sagemaker_client")
    def test_successful_invocation(self, mock_get_client):
        mock_client = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({"predictions": [{"entity": "Housing"}]}).encode("utf-8")
        mock_client.invoke_endpoint.return_value = {"Body": mock_body}
        mock_get_client.return_value = mock_client

        result = _call_sagemaker_endpoint("Patient has housing issues", "test-endpoint")

        mock_client.invoke_endpoint.assert_called_once_with(
            EndpointName="test-endpoint",
            Body=json.dumps({"text": "Patient has housing issues"}),
            ContentType="application/json",
        )
        parsed = json.loads(result)
        assert parsed["predictions"][0]["entity"] == "Housing"

    @patch("agent.agent_config.agent._get_sagemaker_client")
    def test_endpoint_error_propagates(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.invoke_endpoint.side_effect = Exception("Endpoint not found")
        mock_get_client.return_value = mock_client

        with self.assertRaises(Exception) as ctx:
            _call_sagemaker_endpoint("text", "bad-endpoint")
        assert "Endpoint not found" in str(ctx.exception)


class TestExtractSocialDeterminantsOfHealth(unittest.TestCase):
    @patch("agent.agent_config.agent._call_sagemaker_endpoint")
    def test_successful_extraction(self, mock_call):
        mock_call.return_value = json.dumps({"predictions": [{"entity": "Access_To_Care"}]})
        result = extract_social_determinants_of_health(medical_text="Patient lacks access to care")
        assert "Social Determinants of Health" in result
        assert "Access_To_Care" in result
        mock_call.assert_called_once_with(
            "Patient lacks access to care",
            "JSL-Extract-Social-Determinants-of-Health",
        )

    @patch("agent.agent_config.agent._call_sagemaker_endpoint")
    def test_empty_text_returns_error(self, mock_call):
        result = extract_social_determinants_of_health(medical_text="")
        assert "Error" in result
        mock_call.assert_not_called()

    @patch("agent.agent_config.agent._call_sagemaker_endpoint")
    def test_whitespace_only_returns_error(self, mock_call):
        result = extract_social_determinants_of_health(medical_text="   ")
        assert "Error" in result
        mock_call.assert_not_called()


class TestExtractICD10CMSentenceEntities(unittest.TestCase):
    @patch("agent.agent_config.agent._call_sagemaker_endpoint")
    def test_successful_extraction(self, mock_call):
        mock_call.return_value = json.dumps({"predictions": [{"code": "C18", "entity": "colon cancer"}]})
        result = extract_icd_10_cm_sentence_entities(medical_text="Patient diagnosed with colon cancer")
        assert "ICD-10-CM" in result
        assert "C18" in result
        mock_call.assert_called_once_with(
            "Patient diagnosed with colon cancer",
            "ICD-10-CM-Sentence-Entity-Resolver",
        )

    @patch("agent.agent_config.agent._call_sagemaker_endpoint")
    def test_empty_text_returns_error(self, mock_call):
        result = extract_icd_10_cm_sentence_entities(medical_text="")
        assert "Error" in result
        mock_call.assert_not_called()


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
        assert call_kwargs["system_prompt"] == SYSTEM_PROMPT
        assert len(call_kwargs["tools"]) == 2

    def test_system_prompt_contains_guidelines(self):
        assert "medical text analysis" in SYSTEM_PROMPT.lower()
        assert "not providing medical advice" in SYSTEM_PROMPT.lower()


if __name__ == "__main__":
    unittest.main()
