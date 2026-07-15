"""Unit tests for the S3 trigger Lambda function."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def trigger_env(monkeypatch):
    monkeypatch.setenv("AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123:runtime/test")
    monkeypatch.setenv("AWS_REGION", "us-east-1")


@pytest.fixture
def s3_event():
    """Factory for S3 notification events."""
    def _make(bucket="amzn-s3-demo-source-bucket", key="labels/US_FDA/20240101_label.png"):
        return {
            "Records": [{
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key},
                }
            }]
        }
    return _make


@pytest.fixture
def trigger_handler():
    """Import trigger handler with mocked boto3."""
    with patch("boto3.client") as mock_client:
        import importlib
        import sys
        if "index" in sys.modules:
            del sys.modules["index"]
        # Add trigger path
        trigger_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "lambda_functions", "trigger"
        )
        sys.path.insert(0, trigger_path)
        import index as trigger_module
        sys.path.pop(0)
        yield trigger_module, mock_client


class TestTriggerLambdaHandler:
    def test_successful_trigger_with_tags(self, s3_event, fake_lambda_context, trigger_env):
        with patch("boto3.client") as mock_boto3_client:
            s3_mock = MagicMock()
            agentcore_mock = MagicMock()

            def client_factory(service, **kwargs):
                if service == "s3":
                    return s3_mock
                return agentcore_mock

            mock_boto3_client.side_effect = client_factory

            s3_mock.get_object_tagging.return_value = {
                "TagSet": [
                    {"Key": "regulatory_region", "Value": "UK_MHRA"},
                    {"Key": "project_id", "Value": "proj-456"},
                ]
            }

            import importlib
            import sys
            trigger_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "lambda_functions", "trigger"
            )
            sys.path.insert(0, trigger_path)
            if "index" in sys.modules:
                del sys.modules["index"]
            import index as trigger_module
            sys.path.pop(0)

            result = trigger_module.lambda_handler(s3_event(), fake_lambda_context)

            assert result["statusCode"] == 202
            body = json.loads(result["body"])
            assert body["status"] == "triggered"
            assert body["region"] == "UK_MHRA"
            assert "test-request-id" in body["session_id"]

    def test_handles_missing_tags_gracefully(self, s3_event, fake_lambda_context, trigger_env):
        with patch("boto3.client") as mock_boto3_client:
            s3_mock = MagicMock()
            agentcore_mock = MagicMock()

            def client_factory(service, **kwargs):
                if service == "s3":
                    return s3_mock
                return agentcore_mock

            mock_boto3_client.side_effect = client_factory
            s3_mock.get_object_tagging.side_effect = Exception("AccessDenied")

            import sys
            trigger_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "lambda_functions", "trigger"
            )
            sys.path.insert(0, trigger_path)
            if "index" in sys.modules:
                del sys.modules["index"]
            import index as trigger_module
            sys.path.pop(0)

            result = trigger_module.lambda_handler(s3_event(), fake_lambda_context)
            assert result["statusCode"] == 202
            body = json.loads(result["body"])
            assert body["region"] is None

    def test_timeout_error_is_swallowed(self, s3_event, fake_lambda_context, trigger_env):
        with patch("boto3.client") as mock_boto3_client:
            s3_mock = MagicMock()
            agentcore_mock = MagicMock()

            def client_factory(service, **kwargs):
                if service == "s3":
                    return s3_mock
                return agentcore_mock

            mock_boto3_client.side_effect = client_factory
            s3_mock.get_object_tagging.return_value = {"TagSet": []}
            agentcore_mock.invoke_agent_runtime.side_effect = Exception("ReadTimeoutError: timed out")

            import sys
            trigger_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "lambda_functions", "trigger"
            )
            sys.path.insert(0, trigger_path)
            if "index" in sys.modules:
                del sys.modules["index"]
            import index as trigger_module
            sys.path.pop(0)

            result = trigger_module.lambda_handler(s3_event(), fake_lambda_context)
            assert result["statusCode"] == 202

    def test_non_timeout_error_is_raised(self, s3_event, fake_lambda_context, trigger_env):
        with patch("boto3.client") as mock_boto3_client:
            s3_mock = MagicMock()
            agentcore_mock = MagicMock()

            def client_factory(service, **kwargs):
                if service == "s3":
                    return s3_mock
                return agentcore_mock

            mock_boto3_client.side_effect = client_factory
            s3_mock.get_object_tagging.return_value = {"TagSet": []}
            agentcore_mock.invoke_agent_runtime.side_effect = Exception("AccessDenied: not authorized")

            import sys
            trigger_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "lambda_functions", "trigger"
            )
            sys.path.insert(0, trigger_path)
            if "index" in sys.modules:
                del sys.modules["index"]
            import index as trigger_module
            sys.path.pop(0)

            with pytest.raises(Exception, match="AccessDenied"):
                trigger_module.lambda_handler(s3_event(), fake_lambda_context)

    def test_url_decodes_key(self, fake_lambda_context, trigger_env):
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "amzn-s3-demo-source-bucket"},
                    "object": {"key": "labels/US_FDA/file+with+spaces.png"},
                }
            }]
        }
        with patch("boto3.client") as mock_boto3_client:
            s3_mock = MagicMock()
            agentcore_mock = MagicMock()

            def client_factory(service, **kwargs):
                if service == "s3":
                    return s3_mock
                return agentcore_mock

            mock_boto3_client.side_effect = client_factory
            s3_mock.get_object_tagging.return_value = {"TagSet": []}

            import sys
            trigger_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "lambda_functions", "trigger"
            )
            sys.path.insert(0, trigger_path)
            if "index" in sys.modules:
                del sys.modules["index"]
            import index as trigger_module
            sys.path.pop(0)

            trigger_module.lambda_handler(event, fake_lambda_context)

            # Verify the decoded key was used for tagging
            s3_mock.get_object_tagging.assert_called_with(
                Bucket="amzn-s3-demo-source-bucket", Key="labels/US_FDA/file with spaces.png"
            )
