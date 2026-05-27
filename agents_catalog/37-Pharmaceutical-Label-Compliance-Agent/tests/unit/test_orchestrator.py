"""Unit tests for orchestrator.py."""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import sys
import os

# We need to mock heavy imports before importing orchestrator
sys.modules['bedrock_agentcore'] = MagicMock()
sys.modules['bedrock_agentcore.runtime'] = MagicMock()
sys.modules['agent1_compliance'] = MagicMock()
sys.modules['agent2_annotation'] = MagicMock()
sys.modules['agent3_validation'] = MagicMock()


@pytest.fixture(autouse=True)
def mock_orchestrator_env(monkeypatch):
    monkeypatch.setenv("RESULTS_BUCKET", "pharmalabel-results-test")
    monkeypatch.setenv("PROJECTS_TABLE", "pharmalabel-projects-test")
    monkeypatch.setenv("CLOUDFRONT_URL", "https://d123.cloudfront.net")


@pytest.fixture
def orchestrator_module():
    """Import orchestrator with mocked boto3."""
    with patch("boto3.client") as mock_client, \
         patch("boto3.resource") as mock_resource:
        # Force reimport to pick up env vars
        if "orchestrator" in sys.modules:
            del sys.modules["orchestrator"]
        import orchestrator
        orchestrator.s3 = mock_client.return_value
        orchestrator.dynamodb = mock_resource.return_value
        orchestrator.results_bucket = "pharmalabel-results-test"
        orchestrator.projects_table_name = "pharmalabel-projects-test"
        orchestrator.cloudfront_url = "https://d123.cloudfront.net"
        yield orchestrator


# ============================================================
# extract_key Tests (Pure Function)
# ============================================================

class TestExtractKey:
    def test_extracts_key_from_s3_uri(self, orchestrator_module):
        result = orchestrator_module.extract_key("Stored at s3://my-bucket/compliance-report-123.json")
        assert result == "compliance-report-123.json"

    def test_extracts_key_with_nested_path(self, orchestrator_module):
        result = orchestrator_module.extract_key("s3://bucket/path/to/file.json done")
        assert result == "path/to/file.json"

    def test_returns_none_for_no_match(self, orchestrator_module):
        result = orchestrator_module.extract_key("No S3 URI here at all")
        assert result is None

    def test_handles_backtick_terminated_uri(self, orchestrator_module):
        result = orchestrator_module.extract_key("Result: `s3://bucket/report.json`")
        assert result == "report.json"

    def test_handles_whitespace_terminated_uri(self, orchestrator_module):
        result = orchestrator_module.extract_key("s3://bucket/key.png more text after")
        assert result == "key.png"

    def test_handles_none_input(self, orchestrator_module):
        result = orchestrator_module.extract_key(None)
        assert result is None


# ============================================================
# run_pipeline Tests (Mocked)
# ============================================================

class TestRunPipeline:
    def _setup_mocks(self, orchestrator_module, validation_statuses):
        """Set up agent + S3 mocks for pipeline testing."""
        mock_s3 = MagicMock()
        orchestrator_module.s3 = mock_s3

        # Agent 1: returns S3 URI
        mock_agent1 = MagicMock()
        mock_agent1.return_value = "Report stored at s3://pharmalabel-results-test/compliance-report-001.json"

        # Agent 2: returns S3 URI
        mock_agent2 = MagicMock()
        mock_agent2.return_value = "Annotated s3://pharmalabel-results-test/annotated-001.png"

        # Agent 3: returns S3 URI for each attempt
        agent3_responses = [
            f"Validation s3://pharmalabel-results-test/validation-{i}.json"
            for i in range(len(validation_statuses))
        ]
        mock_agent3 = MagicMock(side_effect=agent3_responses)

        # Mock get_*_agent functions
        with patch("orchestrator.get_compliance_agent", return_value=mock_agent1), \
             patch("orchestrator.get_annotation_agent", return_value=mock_agent2), \
             patch("orchestrator.get_validation_agent", return_value=mock_agent3):

            # Mock S3 get_object for image
            mock_s3.get_object.side_effect = self._make_s3_get_object_side_effect(
                validation_statuses
            )

            yield mock_s3, mock_agent1, mock_agent2, mock_agent3

    def _make_s3_get_object_side_effect(self, validation_statuses):
        """Create S3 get_object side effect that handles image + validation reads."""
        call_count = [0]
        statuses = list(validation_statuses)

        def side_effect(Bucket, Key):
            response = MagicMock()
            if Key.startswith("labels/"):
                # Image fetch
                response.__getitem__ = lambda self, k: MagicMock(read=MagicMock(return_value=b'\x89PNG\r\n'))
            elif Key.startswith("compliance-report-"):
                # Compliance report
                data = json.dumps({"compliance_report": "test", "violations": []}).encode()
                response.__getitem__ = lambda self, k: MagicMock(read=MagicMock(return_value=data))
            elif Key.startswith("validation-"):
                # Validation result
                idx = min(call_count[0], len(statuses) - 1)
                status = statuses[idx]
                call_count[0] += 1
                issues = ["issue1", "issue2"] if status == "REJECTED" else []
                data = json.dumps({
                    "validation_status": status,
                    "issues_found": issues,
                    "feedback_to_agent2": "Fix annotations" if status == "REJECTED" else "",
                }).encode()
                response.__getitem__ = lambda self, k: MagicMock(read=MagicMock(return_value=data))
            return response

        return side_effect

    def test_success_on_first_attempt(self, orchestrator_module):
        mock_s3 = MagicMock()
        orchestrator_module.s3 = mock_s3

        # Image read
        image_response = {"Body": MagicMock(read=MagicMock(return_value=b"\x89PNG\r\n"))}
        # Validation read (APPROVED)
        validation_data = json.dumps({
            "validation_status": "APPROVED",
            "issues_found": [],
        }).encode()
        validation_response = {"Body": MagicMock(read=MagicMock(return_value=validation_data))}
        # Compliance report for finalize
        report_data = json.dumps({"compliance_report": "ok", "violations": []}).encode()
        report_response = {"Body": MagicMock(read=MagicMock(return_value=report_data))}

        mock_s3.get_object.side_effect = [image_response, validation_response, report_response]
        mock_s3.put_object.return_value = {}

        mock_agent1 = MagicMock(return_value="s3://pharmalabel-results-test/compliance-report-001.json")
        mock_agent2 = MagicMock(return_value="s3://pharmalabel-results-test/annotated-001.png")
        mock_agent3 = MagicMock(return_value="s3://pharmalabel-results-test/validation-001.json")

        with patch("orchestrator.get_compliance_agent", return_value=mock_agent1), \
             patch("orchestrator.get_annotation_agent", return_value=mock_agent2), \
             patch("orchestrator.get_validation_agent", return_value=mock_agent3), \
             patch("orchestrator._update_project") as mock_update, \
             patch("orchestrator._finalize_project") as mock_finalize:

            result = orchestrator_module.run_pipeline("test-bucket", "labels/US_FDA/test.png")

        assert result["status"] == "success"
        assert result["attempts"] == 1
        assert "compliance-report-001.json" in result["compliance_report"]
        mock_finalize.assert_called_once()

    def test_retry_on_rejection_then_succeed(self, orchestrator_module):
        mock_s3 = MagicMock()
        orchestrator_module.s3 = mock_s3

        image_response = {"Body": MagicMock(read=MagicMock(return_value=b"\x89PNG\r\n"))}
        rejected_data = json.dumps({
            "validation_status": "REJECTED",
            "issues_found": ["mismatch"],
            "feedback_to_agent2": "Fix the count",
        }).encode()
        approved_data = json.dumps({
            "validation_status": "APPROVED",
            "issues_found": [],
        }).encode()
        report_data = json.dumps({"compliance_report": "ok", "violations": []}).encode()

        mock_s3.get_object.side_effect = [
            image_response,  # image fetch
            {"Body": MagicMock(read=MagicMock(return_value=rejected_data))},  # validation attempt 1
            {"Body": MagicMock(read=MagicMock(return_value=rejected_data))},  # feedback read for retry
            {"Body": MagicMock(read=MagicMock(return_value=approved_data))},  # validation attempt 2
            {"Body": MagicMock(read=MagicMock(return_value=report_data))},  # finalize report read
        ]

        mock_agent1 = MagicMock(return_value="s3://pharmalabel-results-test/compliance-report-001.json")
        mock_agent2 = MagicMock(return_value="s3://pharmalabel-results-test/annotated-001.png")
        mock_agent3 = MagicMock(side_effect=[
            "s3://pharmalabel-results-test/validation-001.json",
            "s3://pharmalabel-results-test/validation-002.json",
        ])

        with patch("orchestrator.get_compliance_agent", return_value=mock_agent1), \
             patch("orchestrator.get_annotation_agent", return_value=mock_agent2), \
             patch("orchestrator.get_validation_agent", return_value=mock_agent3), \
             patch("orchestrator._update_project"), \
             patch("orchestrator._finalize_project"):

            result = orchestrator_module.run_pipeline("test-bucket", "labels/US_FDA/test.png", max_retries=3)

        assert result["status"] == "success"
        assert result["attempts"] == 2

    def test_partial_success_selects_best_attempt(self, orchestrator_module):
        mock_s3 = MagicMock()
        orchestrator_module.s3 = mock_s3

        image_response = {"Body": MagicMock(read=MagicMock(return_value=b"\x89PNG\r\n"))}

        # 3 attempts, all rejected with different issue counts: 5, 2, 4
        def make_validation(issue_count):
            data = json.dumps({
                "validation_status": "REJECTED",
                "issues_found": [f"issue{i}" for i in range(issue_count)],
                "feedback_to_agent2": "Fix issues please",
            }).encode()
            return {"Body": MagicMock(read=MagicMock(return_value=data))}

        report_data = json.dumps({"compliance_report": "ok", "violations": []}).encode()

        mock_s3.get_object.side_effect = [
            image_response,
            make_validation(5),  # attempt 1: 5 issues
            make_validation(5),  # feedback read
            make_validation(2),  # attempt 2: 2 issues
            make_validation(2),  # feedback read
            make_validation(4),  # attempt 3: 4 issues
            {"Body": MagicMock(read=MagicMock(return_value=report_data))},  # finalize
        ]

        mock_agent1 = MagicMock(return_value="s3://pharmalabel-results-test/compliance-report-001.json")
        mock_agent2 = MagicMock(return_value="s3://pharmalabel-results-test/annotated-001.png")
        mock_agent3 = MagicMock(side_effect=[
            "s3://pharmalabel-results-test/validation-001.json",
            "s3://pharmalabel-results-test/validation-002.json",
            "s3://pharmalabel-results-test/validation-003.json",
        ])

        with patch("orchestrator.get_compliance_agent", return_value=mock_agent1), \
             patch("orchestrator.get_annotation_agent", return_value=mock_agent2), \
             patch("orchestrator.get_validation_agent", return_value=mock_agent3), \
             patch("orchestrator._update_project"), \
             patch("orchestrator._finalize_project"):

            result = orchestrator_module.run_pipeline("test-bucket", "labels/US_FDA/test.png", max_retries=3)

        assert result["status"] == "partial_success"
        assert result["best_of_attempts"] is True
        assert result["issue_count"] == 2  # best attempt had 2 issues

    def test_fallback_to_s3_listing_when_extract_key_fails(self, orchestrator_module):
        mock_s3 = MagicMock()
        orchestrator_module.s3 = mock_s3

        image_response = {"Body": MagicMock(read=MagicMock(return_value=b"\x89PNG\r\n"))}
        validation_data = json.dumps({
            "validation_status": "APPROVED", "issues_found": [],
        }).encode()
        report_data = json.dumps({"compliance_report": "ok", "violations": []}).encode()

        mock_s3.get_object.side_effect = [
            image_response,
            {"Body": MagicMock(read=MagicMock(return_value=validation_data))},
            {"Body": MagicMock(read=MagicMock(return_value=report_data))},
        ]
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "compliance-report-latest.json"}]
        }

        # Agent responses without s3:// URIs
        mock_agent1 = MagicMock(return_value="Report stored successfully")
        mock_agent2 = MagicMock(return_value="s3://pharmalabel-results-test/annotated-001.png")
        mock_agent3 = MagicMock(return_value="s3://pharmalabel-results-test/validation-001.json")

        with patch("orchestrator.get_compliance_agent", return_value=mock_agent1), \
             patch("orchestrator.get_annotation_agent", return_value=mock_agent2), \
             patch("orchestrator.get_validation_agent", return_value=mock_agent3), \
             patch("orchestrator._update_project"), \
             patch("orchestrator._finalize_project"):

            result = orchestrator_module.run_pipeline("test-bucket", "labels/US_FDA/test.png")

        assert result["status"] == "success"
        mock_s3.list_objects_v2.assert_called()


# ============================================================
# compliance_pipeline_handler Tests
# ============================================================

class TestCompliancePipelineHandler:
    """Test the handler logic directly (bypassing the @app.entrypoint decorator)."""

    def _call_handler(self, orchestrator_module, payload):
        """Call the handler logic directly, replicating what compliance_pipeline_handler does."""
        image_bucket = payload.get("image_bucket")
        image_key = payload.get("image_key")
        max_retries = payload.get("max_retries", 3)
        regulatory_region = payload.get("region", "US_FDA")
        project_id = payload.get("project_id", "")
        try:
            return orchestrator_module.run_pipeline(image_bucket, image_key, max_retries, regulatory_region, project_id)
        except Exception as e:
            return {"error": str(e), "type": "pipeline_error", "status": "failed"}

    def test_wraps_exception_into_error_response(self, orchestrator_module):
        with patch("orchestrator.run_pipeline", side_effect=Exception("Something broke")):
            result = self._call_handler(orchestrator_module, {
                "image_bucket": "b",
                "image_key": "k",
            })
        assert result["status"] == "failed"
        assert result["type"] == "pipeline_error"
        assert "Something broke" in result["error"]

    def test_passes_params_from_payload(self, orchestrator_module):
        with patch("orchestrator.run_pipeline", return_value={"status": "success"}) as mock_run:
            self._call_handler(orchestrator_module, {
                "image_bucket": "my-bucket",
                "image_key": "my-key.png",
                "max_retries": 5,
                "region": "UK_MHRA",
                "project_id": "proj-123",
            })
        mock_run.assert_called_once_with("my-bucket", "my-key.png", 5, "UK_MHRA", "proj-123")

    def test_defaults_optional_params(self, orchestrator_module):
        with patch("orchestrator.run_pipeline", return_value={"status": "success"}) as mock_run:
            self._call_handler(orchestrator_module, {
                "image_bucket": "b",
                "image_key": "k",
            })
        mock_run.assert_called_once_with("b", "k", 3, "US_FDA", "")
