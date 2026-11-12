"""Integration tests for frontend API Lambda with moto S3/DynamoDB."""

import json
import os
import sys
import pytest
from urllib.parse import parse_qs, urlparse
from moto import mock_aws
import boto3

from tests.conftest import USER_A_SUB, USER_B_SUB, make_apigw_event


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    # Placeholder credentials; moto intercepts AWS calls and only needs them set.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "ACCESS_KEY_ID_EXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "SECRET_ACCESS_KEY_EXAMPLE")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "SECURITY_TOKEN_EXAMPLE")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "SESSION_TOKEN_EXAMPLE")
    monkeypatch.setenv("INCOMING_BUCKET", "amzn-s3-demo-source-bucket")
    monkeypatch.setenv("RESULTS_BUCKET", "amzn-s3-demo-destination-bucket")
    monkeypatch.setenv("CLOUDFRONT_URL", "https://d123.cloudfront.net")
    monkeypatch.setenv("PROJECTS_TABLE", "pharmalabel-projects-test")
    monkeypatch.setenv("FRONTEND_ORIGIN", "*")


def _setup_aws():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="amzn-s3-demo-source-bucket")
    s3.create_bucket(Bucket="amzn-s3-demo-destination-bucket")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName="pharmalabel-projects-test",
        KeySchema=[{"AttributeName": "projectId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "projectId", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    return s3, table


def _import_handler():
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


def _call(frontend, path, body=None, sub=USER_A_SUB):
    result = frontend.lambda_handler(make_apigw_event(path, body=body, sub=sub), None)
    return result["statusCode"], json.loads(result["body"]) if result["body"] else None


@mock_aws
class TestProjectsCRUDFlow:
    def test_save_then_list_returns_project(self, aws_env):
        _, table = _setup_aws()
        frontend = _import_handler()

        status, _ = _call(frontend, "/projects/save", {
            "project": {"id": "proj-1", "name": "Test", "region": "US_FDA"}
        })
        assert status == 200

        status, items = _call(frontend, "/projects/list")
        assert len(items) == 1
        assert items[0]["projectId"] == "proj-1"
        assert items[0]["name"] == "Test"
        # Owner recorded server-side from the token.
        assert table.get_item(Key={"projectId": "proj-1"})["Item"]["ownerSub"] == USER_A_SUB

    def test_save_merge_does_not_overwrite_existing_fields(self, aws_env):
        _setup_aws()
        frontend = _import_handler()

        _call(frontend, "/projects/save", {
            "project": {"id": "proj-1", "name": "Original", "region": "US_FDA"}
        })
        _call(frontend, "/projects/save", {
            "project": {"id": "proj-1", "status": "processing"}
        })

        _, items = _call(frontend, "/projects/list")
        proj = items[0]
        assert proj["name"] == "Original"  # not overwritten
        assert proj["region"] == "US_FDA"  # not overwritten
        assert proj["status"] == "processing"  # newly added

    def test_delete_removes_from_table(self, aws_env):
        _setup_aws()
        frontend = _import_handler()

        _call(frontend, "/projects/save", {"project": {"id": "proj-1", "name": "To Delete"}})

        status, body = _call(frontend, "/projects/delete", {"id": "proj-1"})
        assert status == 200
        assert body["deleted"] == "proj-1"

        _, items = _call(frontend, "/projects/list")
        assert items == []

    def test_upload_for_own_project_tags_object_with_project_id(self, aws_env):
        _setup_aws()
        frontend = _import_handler()
        _call(frontend, "/projects/save", {"project": {"id": "proj-1", "name": "Mine"}})

        status, body = _call(frontend, "/upload", {
            "filename": "label.png", "contentType": "image/png", "region": "US_FDA", "projectId": "proj-1"
        })
        assert status == 200
        query = parse_qs(urlparse(body["uploadUrl"]).query)
        tags = parse_qs(query["x-amz-tagging"][0])
        assert tags == {"regulatory_region": ["US_FDA"], "project_id": ["proj-1"]}


@mock_aws
class TestCheckFlowDynamo:
    def test_complete_project_returns_all_fields(self, aws_env):
        _, table = _setup_aws()
        table.put_item(Item={
            "projectId": "proj-1",
            "ownerSub": USER_A_SUB,
            "status": "complete",
            "annotatedImageUrl": "https://d123.cloudfront.net/annotated.png",
            "complianceReport": "Analysis text",
            "formattedViolations": [{"title": "V1", "severity": "high"}],
            "progress": {"step1": True, "step2": True, "step3": True},
        })

        frontend = _import_handler()
        status, body = _call(frontend, "/check", {"projectId": "proj-1"})
        assert status == 200
        assert body["status"] == "completed"
        assert body["annotatedImageUrl"] == "https://d123.cloudfront.net/annotated.png"
        assert len(body["violations"]) == 1


@mock_aws
class TestTenantIsolation:
    """User B attempts every project operation against user A's project."""

    def _seed_user_a_project(self, frontend, table):
        status, _ = _call(frontend, "/projects/save", {
            "project": {"id": "proj-a", "name": "A's label", "region": "US_FDA"}
        }, sub=USER_A_SUB)
        assert status == 200
        # Simulate the pipeline having finished for A's project.
        table.update_item(
            Key={"projectId": "proj-a"},
            UpdateExpression="SET #s = :s, complianceReport = :r, annotatedImageUrl = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "complete",
                ":r": "CONFIDENTIAL REPORT FOR A",
                ":u": "https://d123.cloudfront.net/a.png",
            },
        )

    def test_list_only_returns_callers_projects(self, aws_env):
        _, table = _setup_aws()
        frontend = _import_handler()
        self._seed_user_a_project(frontend, table)
        _call(frontend, "/projects/save", {"project": {"id": "proj-b", "name": "B's label"}}, sub=USER_B_SUB)

        _, a_items = _call(frontend, "/projects/list", sub=USER_A_SUB)
        _, b_items = _call(frontend, "/projects/list", sub=USER_B_SUB)
        assert [p["projectId"] for p in a_items] == ["proj-a"]
        assert [p["projectId"] for p in b_items] == ["proj-b"]

    def test_other_user_cannot_read_results(self, aws_env):
        _, table = _setup_aws()
        frontend = _import_handler()
        self._seed_user_a_project(frontend, table)

        status, body = _call(frontend, "/check", {"projectId": "proj-a"}, sub=USER_B_SUB)
        assert status == 404
        assert "CONFIDENTIAL" not in json.dumps(body)

    def test_other_user_cannot_modify(self, aws_env):
        _, table = _setup_aws()
        frontend = _import_handler()
        self._seed_user_a_project(frontend, table)

        status, _ = _call(frontend, "/projects/save", {
            "project": {"id": "proj-a", "name": "Tampered", "status": "complete", "complianceScore": 100}
        }, sub=USER_B_SUB)
        assert status == 404

        item = table.get_item(Key={"projectId": "proj-a"})["Item"]
        assert item["name"] == "A's label"
        assert item["ownerSub"] == USER_A_SUB
        assert "complianceScore" not in item

    def test_other_user_cannot_take_ownership(self, aws_env):
        _, table = _setup_aws()
        frontend = _import_handler()
        self._seed_user_a_project(frontend, table)

        # Write attempt that also tries to set the owner field.
        status, _ = _call(frontend, "/projects/save", {
            "project": {"id": "proj-a", "name": "Mine now", "ownerSub": USER_B_SUB}
        }, sub=USER_B_SUB)
        assert status == 404

        # Owner field alone is ignored, so nothing is written.
        _call(frontend, "/projects/save", {
            "project": {"id": "proj-a", "ownerSub": USER_B_SUB}
        }, sub=USER_B_SUB)

        item = table.get_item(Key={"projectId": "proj-a"})["Item"]
        assert item["ownerSub"] == USER_A_SUB
        assert item["name"] == "A's label"

    def test_other_user_cannot_delete(self, aws_env):
        _, table = _setup_aws()
        frontend = _import_handler()
        self._seed_user_a_project(frontend, table)

        status, _ = _call(frontend, "/projects/delete", {"id": "proj-a"}, sub=USER_B_SUB)
        assert status == 404
        assert "Item" in table.get_item(Key={"projectId": "proj-a"})

    def test_other_user_cannot_upload_into_project(self, aws_env):
        _, table = _setup_aws()
        frontend = _import_handler()
        self._seed_user_a_project(frontend, table)

        status, body = _call(frontend, "/upload", {
            "filename": "label.png", "contentType": "image/png", "projectId": "proj-a"
        }, sub=USER_B_SUB)
        assert status == 404
        assert "uploadUrl" not in body

    def test_owner_still_has_full_access(self, aws_env):
        _, table = _setup_aws()
        frontend = _import_handler()
        self._seed_user_a_project(frontend, table)

        status, body = _call(frontend, "/check", {"projectId": "proj-a"}, sub=USER_A_SUB)
        assert status == 200
        assert body["complianceReport"] == "CONFIDENTIAL REPORT FOR A"
        assert _call(frontend, "/projects/save", {"project": {"id": "proj-a", "name": "Renamed"}})[0] == 200
        assert _call(frontend, "/projects/delete", {"id": "proj-a"})[0] == 200

    def test_deleting_missing_project_returns_404(self, aws_env):
        _setup_aws()
        frontend = _import_handler()
        status, _ = _call(frontend, "/projects/delete", {"id": "never-existed"})
        assert status == 404

    def test_legacy_records_without_owner_are_hidden_and_locked(self, aws_env):
        """Records created before ownership was added are not visible to or claimable by anyone."""
        _, table = _setup_aws()
        table.put_item(Item={"projectId": "legacy", "name": "Old", "status": "complete"})
        frontend = _import_handler()

        _, items = _call(frontend, "/projects/list")
        assert items == []
        assert _call(frontend, "/check", {"projectId": "legacy"})[0] == 404
        assert _call(frontend, "/projects/save", {"project": {"id": "legacy", "name": "Mine now"}})[0] == 404
        assert _call(frontend, "/projects/delete", {"id": "legacy"})[0] == 404
        assert "ownerSub" not in table.get_item(Key={"projectId": "legacy"})["Item"]
