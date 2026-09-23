"""Unit tests for the Protein Design Agent."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config import agent as agent_module
from agent.agent_config.agent import (
    SYSTEM_PROMPT,
    create_agent,
    monitor_aho_workflow,
    trigger_aho_workflow,
)


class TestTriggerWorkflow(unittest.TestCase):
    def setUp(self):
        # Ensure required config is present for the happy-path tests.
        agent_module.WORKFLOW_ID = "wfl-123"
        agent_module.ROLE_ARN = "arn:aws:iam::111122223333:role/omics-exec"
        agent_module.ECR_URI = "111122223333.dkr.ecr.us-east-1.amazonaws.com/evoprotgrad:latest"
        agent_module.S3_BUCKET = "protein-bucket"
        agent_module.ESM_MODEL_FILES = "s3://protein-bucket/models/esm2/"

    def test_empty_sequence_returns_error(self):
        assert "Error" in trigger_aho_workflow(seed_sequence="")

    @patch("agent.agent_config.agent._get_client")
    def test_missing_workflow_id_returns_error(self, _mock_client):
        agent_module.WORKFLOW_ID = None
        result = trigger_aho_workflow(seed_sequence="ACDE")
        assert "WORKFLOW_ID is not configured" in result

    @patch("agent.agent_config.agent._get_client")
    def test_successful_start_run(self, mock_get_client):
        mock_omics = MagicMock()
        mock_omics.start_run.return_value = {"id": "run-789", "status": "PENDING"}
        mock_get_client.return_value = mock_omics

        result = trigger_aho_workflow(seed_sequence="ACDEFGHIK", n_steps=200)

        assert "run-789" in result
        assert "PENDING" in result
        _, kwargs = mock_omics.start_run.call_args
        assert kwargs["workflowId"] == "wfl-123"
        assert kwargs["roleArn"] == "arn:aws:iam::111122223333:role/omics-exec"
        params = kwargs["parameters"]
        assert params["seed_sequence"] == "ACDEFGHIK"
        assert params["container_image"].endswith("evoprotgrad:latest")
        assert params["n_steps"] == 200  # override honored
        assert params["parallel_chains"] == 10  # default
        assert params["esm_model_files"] == "s3://protein-bucket/models/esm2/"
        assert kwargs["outputUri"].startswith("s3://protein-bucket/outputs/")

    @patch("agent.agent_config.agent._get_client")
    def test_start_run_error_returns_message(self, mock_get_client):
        mock_omics = MagicMock()
        mock_omics.start_run.side_effect = Exception("AccessDenied")
        mock_get_client.return_value = mock_omics

        result = trigger_aho_workflow(seed_sequence="ACDE")
        assert "Error starting workflow run" in result


class TestMonitorWorkflow(unittest.TestCase):
    def test_empty_run_id_returns_error(self):
        assert "Error" in monitor_aho_workflow(run_id="")

    @patch("agent.agent_config.agent._get_client")
    def test_running_status(self, mock_get_client):
        mock_omics = MagicMock()
        mock_omics.get_run.return_value = {"status": "RUNNING", "name": "run-a"}
        mock_get_client.return_value = mock_omics

        result = monitor_aho_workflow(run_id="run-a")
        assert "RUNNING" in result
        assert "still running" in result

    @patch("agent.agent_config.agent._get_client")
    def test_failed_status(self, mock_get_client):
        mock_omics = MagicMock()
        mock_omics.get_run.return_value = {"status": "FAILED", "statusMessage": "OOM"}
        mock_get_client.return_value = mock_omics

        result = monitor_aho_workflow(run_id="run-b")
        assert "FAILED" in result
        assert "OOM" in result

    @patch("agent.agent_config.agent._get_client")
    def test_completed_status_summarizes_results(self, mock_get_client):
        mock_omics = MagicMock()
        mock_omics.get_run.return_value = {
            "status": "COMPLETED",
            "name": "run-c",
            "outputUri": "s3://protein-bucket/outputs/run-c/",
        }
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "outputs/run-c/de/de_results.csv", "Size": 500}]
        }
        body = MagicMock()
        body.read.return_value = b"sequence,score\nACDE,0.91\n"
        mock_s3.get_object.return_value = {"Body": body}

        # First _get_client("omics") -> omics, second _get_client("s3") -> s3
        mock_get_client.side_effect = [mock_omics, mock_s3]

        result = monitor_aho_workflow(run_id="run-c")
        assert "COMPLETED" in result
        assert "de_results.csv" in result
        assert "Results summary" in result
        assert "ACDE,0.91" in result

    @patch("agent.agent_config.agent._get_client")
    def test_get_run_error_returns_message(self, mock_get_client):
        mock_omics = MagicMock()
        mock_omics.get_run.side_effect = Exception("RunNotFound")
        mock_get_client.return_value = mock_omics

        result = monitor_aho_workflow(run_id="bad")
        assert "Error monitoring workflow" in result


class TestCreateAgent(unittest.TestCase):
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent_with_correct_config(self, mock_agent_cls, mock_model_cls):
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        create_agent()

        mock_model_cls.assert_called_once_with(model_id=agent_module.MODEL_ID, streaming=True)
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["system_prompt"] == SYSTEM_PROMPT
        assert len(call_kwargs["tools"]) == 2

    def test_system_prompt_mentions_healthomics(self):
        assert "healthomics" in SYSTEM_PROMPT.lower()
        assert "protein design" in SYSTEM_PROMPT.lower()


if __name__ == "__main__":
    unittest.main()
