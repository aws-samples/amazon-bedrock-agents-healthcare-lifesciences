"""Integration tests for frontend API Lambda with moto S3/DynamoDB."""

import json
import os
import sys
import pytest
from moto import mock_aws
import boto3


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("INCOMING_BUCKET", "pharmalabel-incoming-test")
    monkeypatch.setenv("RESULTS_BUCKET", "pharmalabel-results-test")
    monkeypatch.setenv("CLOUDFRONT_URL", "https://d123.cloudfront.net")
    monkeypatch.setenv("PROJECTS_TABLE", "pharmalabel-projects-test")
    monkeypatch.setenv("FRONTEND_ORIGIN", "*")


@mock_aws
class TestProjectsCRUDFlow:
    def _setup_aws(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="pharmalabel-incoming-test")
        s3.create_bucket(Bucket="pharmalabel-results-test")
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="pharmalabel-projects-test",
            KeySchema=[{"AttributeName": "projectId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "projectId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        return s3, dynamodb

    def _import_handler(self):
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "lambda_functions", "frontend_api"
        )
        sys.path.insert(0, frontend_path)
        if "index" in sys.modules:
            del sys.modules["index"]
        import index as frontend
        sys.path.pop(0)
        return frontend

    def _make_event(self, path, body=None):
        return {
            "rawPath": path,
            "requestContext": {"http": {"method": "POST"}},
            "headers": {"origin": "*"},
            "body": json.dumps(body or {}),
        }

    def test_save_then_list_returns_project(self, aws_env):
        self._setup_aws()
        frontend = self._import_handler()

        # Save a project
        save_event = self._make_event("/projects/save", {
            "project": {"id": "proj-1", "name": "Test", "region": "US_FDA"}
        })
        save_result = frontend.lambda_handler(save_event, None)
        assert save_result["statusCode"] == 200

        # List projects
        list_event = self._make_event("/projects/list")
        list_result = frontend.lambda_handler(list_event, None)
        items = json.loads(list_result["body"])
        assert len(items) == 1
        assert items[0]["projectId"] == "proj-1"
        assert items[0]["name"] == "Test"

    def test_save_merge_does_not_overwrite_existing_fields(self, aws_env):
        self._setup_aws()
        frontend = self._import_handler()

        # Save initial project with name + region
        frontend.lambda_handler(self._make_event("/projects/save", {
            "project": {"id": "proj-1", "name": "Original", "region": "US_FDA"}
        }), None)

        # Save again with different field only
        frontend.lambda_handler(self._make_event("/projects/save", {
            "project": {"id": "proj-1", "status": "processing"}
        }), None)

        # List and verify original fields preserved
        list_result = frontend.lambda_handler(self._make_event("/projects/list"), None)
        items = json.loads(list_result["body"])
        proj = items[0]
        assert proj["name"] == "Original"  # not overwritten
        assert proj["region"] == "US_FDA"  # not overwritten
        assert proj["status"] == "processing"  # newly added

    def test_delete_removes_from_table(self, aws_env):
        self._setup_aws()
        frontend = self._import_handler()

        # Create then delete
        frontend.lambda_handler(self._make_event("/projects/save", {
            "project": {"id": "proj-1", "name": "To Delete"}
        }), None)

        delete_result = frontend.lambda_handler(
            self._make_event("/projects/delete", {"id": "proj-1"}), None
        )
        assert json.loads(delete_result["body"])["deleted"] == "proj-1"

        # Verify empty
        list_result = frontend.lambda_handler(self._make_event("/projects/list"), None)
        assert json.loads(list_result["body"]) == []


@mock_aws
class TestCheckFlowDynamo:
    def _setup(self, aws_env):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="pharmalabel-incoming-test")
        s3.create_bucket(Bucket="pharmalabel-results-test")
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="pharmalabel-projects-test",
            KeySchema=[{"AttributeName": "projectId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "projectId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        return s3, table

    def _import_handler(self):
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "lambda_functions", "frontend_api"
        )
        sys.path.insert(0, frontend_path)
        if "index" in sys.modules:
            del sys.modules["index"]
        import index as frontend
        sys.path.pop(0)
        return frontend

    def test_complete_project_returns_all_fields(self, aws_env):
        _, table = self._setup(aws_env)
        table.put_item(Item={
            "projectId": "proj-1",
            "status": "complete",
            "annotatedImageUrl": "https://d123.cloudfront.net/annotated.png",
            "complianceReport": "Analysis text",
            "formattedViolations": [{"title": "V1", "severity": "high"}],
            "progress": {"step1": True, "step2": True, "step3": True},
        })

        frontend = self._import_handler()
        event = {
            "rawPath": "/check",
            "requestContext": {"http": {"method": "POST"}},
            "headers": {},
            "body": json.dumps({"projectId": "proj-1"}),
        }
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["status"] == "completed"
        assert body["annotatedImageUrl"] == "https://d123.cloudfront.net/annotated.png"
        assert len(body["violations"]) == 1
