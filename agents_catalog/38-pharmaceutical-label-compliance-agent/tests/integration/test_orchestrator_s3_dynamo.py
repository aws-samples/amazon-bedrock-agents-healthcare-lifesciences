"""Integration tests for orchestrator S3/DynamoDB operations using moto."""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3

# Mock heavy imports before loading orchestrator
sys.modules['bedrock_agentcore'] = MagicMock()
sys.modules['bedrock_agentcore.runtime'] = MagicMock()
sys.modules['agent1_compliance'] = MagicMock()
sys.modules['agent2_annotation'] = MagicMock()
sys.modules['agent3_validation'] = MagicMock()


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    # Placeholder credentials; moto intercepts AWS calls and only needs them set.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "ACCESS_KEY_ID_EXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "SECRET_ACCESS_KEY_EXAMPLE")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "SECURITY_TOKEN_EXAMPLE")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "SESSION_TOKEN_EXAMPLE")
    monkeypatch.setenv("RESULTS_BUCKET", "amzn-s3-demo-destination-bucket")
    monkeypatch.setenv("PROJECTS_TABLE", "pharmalabel-projects-test")


@mock_aws
class TestUpdateProject:
    def test_creates_expression_from_updates_dict(self, aws_env):
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="pharmalabel-projects-test",
            KeySchema=[{"AttributeName": "projectId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "projectId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        if "orchestrator" in sys.modules:
            del sys.modules["orchestrator"]
        import orchestrator
        orchestrator.amazon_dynamodb = dynamodb
        orchestrator.projects_table_name = "pharmalabel-projects-test"

        orchestrator._update_project("proj-1", {"status": "processing", "step": 1})

        table = dynamodb.Table("pharmalabel-projects-test")
        resp = table.get_item(Key={"projectId": "proj-1"})
        item = resp["Item"]
        assert item["status"] == "processing"
        assert item["step"] == 1

    def test_no_op_when_project_id_empty(self, aws_env):
        if "orchestrator" in sys.modules:
            del sys.modules["orchestrator"]
        import orchestrator
        orchestrator.amazon_dynamodb = MagicMock()
        orchestrator.projects_table_name = "pharmalabel-projects-test"

        orchestrator._update_project("", {"status": "x"})
        orchestrator.amazon_dynamodb.Table.assert_not_called()

    def test_no_op_when_table_name_empty(self, aws_env):
        if "orchestrator" in sys.modules:
            del sys.modules["orchestrator"]
        import orchestrator
        orchestrator.amazon_dynamodb = MagicMock()
        orchestrator.projects_table_name = ""

        orchestrator._update_project("proj-1", {"status": "x"})
        orchestrator.amazon_dynamodb.Table.assert_not_called()

    def test_handles_dynamodb_error_gracefully(self, aws_env):
        if "orchestrator" in sys.modules:
            del sys.modules["orchestrator"]
        import orchestrator
        mock_dynamo = MagicMock()
        mock_dynamo.Table.return_value.update_item.side_effect = Exception("DynamoDB unavailable")
        orchestrator.amazon_dynamodb = mock_dynamo
        orchestrator.projects_table_name = "pharmalabel-projects-test"

        # Should not raise
        orchestrator._update_project("proj-1", {"status": "x"})


@mock_aws
class TestFinalizeProject:
    def test_writes_completion_marker_and_dynamo(self, aws_env):
        # Setup S3 and DynamoDB
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="amzn-s3-demo-destination-bucket")
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="pharmalabel-projects-test",
            KeySchema=[{"AttributeName": "projectId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "projectId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Seed compliance report
        report = {"compliance_report": "Label analysis", "violations": [{"title": "V1"}]}
        s3.put_object(
            Bucket="amzn-s3-demo-destination-bucket",
            Key="compliance-report-001.json",
            Body=json.dumps(report),
        )

        if "orchestrator" in sys.modules:
            del sys.modules["orchestrator"]
        import orchestrator
        orchestrator.amazon_s3 = s3
        orchestrator.amazon_dynamodb = dynamodb
        orchestrator.results_bucket = "amzn-s3-demo-destination-bucket"
        orchestrator.projects_table_name = "pharmalabel-projects-test"

        # A record from before images were private still has a public URL.
        table = dynamodb.Table("pharmalabel-projects-test")
        table.put_item(Item={
            "projectId": "proj-1",
            "ownerSub": "owner-sub",
            "annotatedImageUrl": "https://d123.cloudfront.net/annotated-old.png",
        })

        orchestrator._finalize_project(
            project_id="proj-1",
            image_key="labels/US_FDA/proj-1/test.png",
            report_key="compliance-report-001.json",
            annotated_key="annotated-001.png",
            validation_key="validation-001.json",
            attempts=2,
            artifact_keys=["annotated-000.png", "validation-000.json", "annotated-001.png", "validation-001.json"],
        )

        # Verify DynamoDB
        resp = table.get_item(Key={"projectId": "proj-1"})
        item = resp["Item"]
        assert item["status"] == "complete"
        assert item["pipelineAttempts"] == 2
        assert item["annotatedKey"] == "annotated-001.png"
        assert item["ownerSub"] == "owner-sub"
        # Images are stored by key only; the stale public URL is removed.
        assert "annotatedImageUrl" not in item

        # Verify S3 completion marker
        objects = s3.list_objects_v2(Bucket="amzn-s3-demo-destination-bucket", Prefix="completion-")
        assert objects["KeyCount"] == 1
        marker_key = objects["Contents"][0]["Key"]

        # The evaluation records every object the run wrote, so deleting the
        # project can remove them (including rejected attempts and the marker).
        evaluation = item["evaluations"][0]
        assert evaluation["annotatedKey"] == "annotated-001.png"
        assert "annotatedImageUrl" not in evaluation
        assert evaluation["artifactKeys"] == sorted([
            "annotated-000.png", "annotated-001.png", "compliance-report-001.json",
            "validation-000.json", "validation-001.json", marker_key,
        ])
        marker = json.loads(s3.get_object(Bucket="amzn-s3-demo-destination-bucket", Key=marker_key)["Body"].read())
        assert marker["status"] == "completed"
        assert marker["annotated_key"] == "annotated-001.png"
        assert marker["attempts"] == 2
        assert marker["project_id"] == "proj-1"
