# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    consult_with_medical_reasoning_model,
    call_sagemaker_endpoint,
    _get_endpoint_name,
    create_agent,
)


class TestGetEndpointName(unittest.TestCase):
    @patch.dict(os.environ, {"ENDPOINT_NAME_1": "my-endpoint"})
    def test_returns_endpoint_name(self):
        assert _get_endpoint_name() == "my-endpoint"

    @patch.dict(os.environ, {}, clear=True)
    def test_raises_when_not_set(self):
        # Remove the key if present
        os.environ.pop("ENDPOINT_NAME_1", None)
        with self.assertRaises(RuntimeError):
            _get_endpoint_name()


class TestCallSagemakerEndpoint(unittest.TestCase):
    @patch("agent.agent_config.agent.sagemaker_runtime")
    def test_successful_invocation(self, mock_sm):
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({
            "choices": [{"message": {"content": "<think>\nreasoning\n</think>\n\n**Final Answer**: Diagnosis X"}}]
        }).encode("utf-8")
        mock_sm.invoke_endpoint.return_value = {"Body": mock_body}

        result = call_sagemaker_endpoint("Patient has fever", "test-endpoint")

        mock_sm.invoke_endpoint.assert_called_once()
        call_kwargs = mock_sm.invoke_endpoint.call_args[1]
        assert call_kwargs["EndpointName"] == "test-endpoint"
        assert call_kwargs["ContentType"] == "application/json"

        body = json.loads(call_kwargs["Body"])
        assert body["messages"][1]["content"] == "Patient has fever"
        assert body["max_tokens"] == 2048
        assert body["temperature"] == 0.8
        assert body["top_p"] == 0.95
        assert body["model"] == "/opt/ml/model"
        assert "medical expert" in body["messages"][0]["content"]

        parsed = json.loads(result)
        assert "choices" in parsed

    @patch("agent.agent_config.agent.sagemaker_runtime")
    def test_endpoint_error_propagates(self, mock_sm):
        mock_sm.invoke_endpoint.side_effect = Exception("Endpoint not found")
        with self.assertRaises(Exception) as ctx:
            call_sagemaker_endpoint("test", "bad-endpoint")
        assert "Endpoint not found" in str(ctx.exception)


class TestConsultWithMedicalReasoningModel(unittest.TestCase):
    @patch("agent.agent_config.agent.call_sagemaker_endpoint")
    @patch.dict(os.environ, {"ENDPOINT_NAME_1": "test-endpoint"})
    def test_returns_formatted_result(self, mock_call):
        mock_call.return_value = '{"choices":[{"message":{"content":"answer"}}]}'
        result = consult_with_medical_reasoning_model(
            medical_text="Patient presents with chest pain"
        )
        assert "Results from medical reasoning model" in result
        mock_call.assert_called_once_with("Patient presents with chest pain", "test-endpoint")

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_endpoint_raises(self):
        os.environ.pop("ENDPOINT_NAME_1", None)
        with self.assertRaises(RuntimeError):
            consult_with_medical_reasoning_model(medical_text="test")


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
        assert "medical" in call_kwargs["system_prompt"].lower()


if __name__ == "__main__":
    unittest.main()
