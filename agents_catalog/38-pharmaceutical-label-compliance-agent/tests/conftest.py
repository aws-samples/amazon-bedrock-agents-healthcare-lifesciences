"""Shared fixtures for the PharmaLabel test suite."""

import json
import os
import sys
import pytest
from unittest.mock import MagicMock

# Add src directories to Python path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _src_dir in (
    PROJECT_ROOT,
    os.path.join(PROJECT_ROOT, "agent_package"),
    os.path.join(PROJECT_ROOT, "lambda_functions", "trigger"),
    os.path.join(PROJECT_ROOT, "lambda_functions", "frontend_api"),
    os.path.join(PROJECT_ROOT, "lambda_functions", "document_management"),
):
    if _src_dir not in sys.path:
        sys.path.append(_src_dir)


# --- Fake Strands Event Classes --- #

class FakeBeforeToolCallEvent:
    """Mimics strands.hooks.BeforeToolCallEvent for unit testing steering plugins."""

    def __init__(self, tool_use: dict):
        self.tool_use = tool_use
        self.cancel_tool = None


class FakeAfterToolCallEvent:
    """Mimics strands.hooks.AfterToolCallEvent for unit testing steering plugins."""

    def __init__(self, tool_use: dict, result=None):
        self.tool_use = tool_use
        self.result = result


# --- Fixtures --- #

@pytest.fixture
def before_event():
    """Factory for creating BeforeToolCallEvent fakes."""
    def _make(tool_name: str, inputs: dict = None):
        tool_use = {"name": tool_name}
        if inputs is not None:
            tool_use["input"] = inputs
        return FakeBeforeToolCallEvent(tool_use)
    return _make


@pytest.fixture
def after_event():
    """Factory for creating AfterToolCallEvent fakes."""
    def _make(tool_name: str, result=None):
        return FakeAfterToolCallEvent({"name": tool_name}, result=result)
    return _make


@pytest.fixture
def sample_violations():
    """A valid violations list with 3 violations covering all severities."""
    return [
        {"title": "Missing Drug Facts header", "description": "No Drug Facts panel header found", "severity": "high"},
        {"title": "Unsubstantiated marketing claim", "description": "Label claims 'clinically proven' without evidence", "severity": "medium"},
        {"title": "Font size below minimum", "description": "Active ingredient text is below 6pt minimum", "severity": "low"},
    ]


@pytest.fixture
def sample_violations_json(sample_violations):
    """JSON string of sample violations."""
    return json.dumps(sample_violations)


@pytest.fixture
def sample_annotations():
    """Valid annotations matching sample_violations."""
    return [
        {"label": "Missing Drug Facts header", "box": [0, 0, 0, 0], "severity": "high"},
        {"label": "Unsubstantiated marketing claim", "box": [100, 200, 400, 250], "severity": "medium"},
        {"label": "Font size below minimum", "box": [50, 300, 350, 330], "severity": "low"},
    ]


@pytest.fixture
def sample_compliance_report(sample_violations):
    """S3 compliance report JSON structure."""
    return {
        "compliance_report": "The label has 3 violations...",
        "violations": sample_violations,
        "source_file": "labels/US_FDA/test_label.png",
    }


@pytest.fixture
def sample_validation_result():
    """S3 validation result JSON structure."""
    return {
        "validation_status": "APPROVED",
        "issues_found": [],
        "feedback_to_agent2": "",
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set all required environment variables for the project."""
    monkeypatch.setenv("INCOMING_BUCKET", "amzn-s3-demo-source-bucket")
    monkeypatch.setenv("RESULTS_BUCKET", "amzn-s3-demo-destination-bucket")
    monkeypatch.setenv("FRONTEND_BUCKET", "amzn-s3-demo-bucket1")
    monkeypatch.setenv("KB_BUCKET", "amzn-s3-demo-bucket2")
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "KB-TEST-123")
    monkeypatch.setenv("PROJECTS_TABLE", "pharmalabel-projects-test")
    monkeypatch.setenv("CLOUDFRONT_URL", "https://d123.cloudfront.net")
    monkeypatch.setenv("AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test-runtime")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://d123.cloudfront.net")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def fake_lambda_context():
    """Fake AWS Lambda context object."""
    ctx = MagicMock()
    ctx.aws_request_id = "test-request-id-12345"
    ctx.function_name = "test-function"
    ctx.memory_limit_in_mb = 512
    ctx.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    return ctx


@pytest.fixture
def apigw_event_factory():
    """Factory for creating API Gateway v2 HTTP events."""
    def _make(path: str, method: str = "POST", body: dict = None):
        return {
            "rawPath": path,
            "requestContext": {"http": {"method": method}},
            "headers": {"origin": "https://d123.cloudfront.net"},
            "body": json.dumps(body) if body else "{}",
        }
    return _make
