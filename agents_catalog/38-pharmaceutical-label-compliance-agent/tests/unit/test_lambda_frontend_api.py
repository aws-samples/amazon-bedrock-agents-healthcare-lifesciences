"""Unit tests for the frontend API Lambda function."""

import json
import os
import sys
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from urllib.parse import parse_qs

from botocore.exceptions import ClientError

from tests.conftest import USER_A_SUB, USER_B_SUB


@pytest.fixture(autouse=True)
def frontend_env(monkeypatch):
    monkeypatch.setenv("INCOMING_BUCKET", "amzn-s3-demo-source-bucket")
    monkeypatch.setenv("RESULTS_BUCKET", "amzn-s3-demo-destination-bucket")
    monkeypatch.setenv("PROJECTS_TABLE", "pharmalabel-projects-test")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://d123.cloudfront.net")


@pytest.fixture
def frontend_module():
    """Import frontend_api/index.py with mocked boto3."""
    with patch("boto3.client") as mock_s3_client, \
         patch("boto3.resource") as mock_dynamo_resource:

        mock_table = MagicMock()
        mock_dynamo_resource.return_value.Table.return_value = mock_table

        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "lambda_functions", "frontend_api"
        )
        sys.path.insert(0, frontend_path)
        if "index" in sys.modules:
            del sys.modules["index"]
        import index as frontend
        sys.path.pop(0)

        frontend.amazon_s3 = mock_s3_client.return_value
        frontend.amazon_s3_signer = mock_s3_client.return_value
        frontend.projects_table = mock_table
        yield frontend, mock_s3_client.return_value, mock_table


def owned_by(sub, **fields):
    """A DynamoDB get_item response for a project owned by `sub`."""
    return {"Item": {"projectId": "proj-1", "ownerSub": sub, **fields}}


def conditional_check_failed(operation):
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "The conditional request failed"}},
        operation,
    )


# ============================================================
# Request Routing Tests
# ============================================================

class TestRequestRouting:
    def test_routes_to_upload(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(USER_A_SUB)
        mock_s3.generate_presigned_url.return_value = "https://presigned.url"
        event = apigw_event_factory("/upload", body={
            "filename": "test.png", "contentType": "image/png", "projectId": "proj-1"
        })
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_routes_to_check(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(USER_A_SUB, status="processing", progress={})
        event = apigw_event_factory("/check", body={"projectId": "proj-1"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_routes_to_projects_list(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.scan.return_value = {"Items": []}
        event = apigw_event_factory("/projects/list")
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_returns_404_for_unknown_path(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/nonexistent")
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 404

    def test_options_returns_cors_headers(self, frontend_module):
        frontend, _, _ = frontend_module
        event = {
            "rawPath": "/upload",
            "requestContext": {"http": {"method": "OPTIONS"}},
            "headers": {},
            "body": "",
        }
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]

    def test_internal_error_returns_500(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(USER_A_SUB)
        mock_s3.generate_presigned_url.side_effect = Exception("boom")
        event = apigw_event_factory("/upload", body={
            "filename": "test.png", "contentType": "image/png", "projectId": "proj-1"
        })
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 500

    def test_invalid_json_returns_400(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/projects/save", raw_body="{not json")
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400


# ============================================================
# Caller identity (authentication context) Tests
# ============================================================

class TestCallerIdentity:
    @pytest.mark.parametrize("path", [
        "/upload", "/check", "/projects/list", "/projects/save", "/projects/delete",
    ])
    def test_rejects_request_without_verified_identity(self, frontend_module, apigw_event_factory, path):
        frontend, mock_s3, mock_table = frontend_module
        event = apigw_event_factory(path, body={"projectId": "proj-1", "id": "proj-1"}, sub=None)
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 401
        # Nothing is read or written without an identity.
        mock_table.get_item.assert_not_called()
        mock_table.scan.assert_not_called()
        mock_table.update_item.assert_not_called()
        mock_table.delete_item.assert_not_called()
        mock_s3.generate_presigned_url.assert_not_called()

    def test_rejects_empty_sub(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/projects/list", sub="")
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 401

    def test_options_does_not_require_identity(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/projects/list", method="OPTIONS", sub=None)
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_get_caller_sub_reads_jwt_claims(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        assert frontend._get_caller_sub(apigw_event_factory("/x", sub=USER_B_SUB)) == USER_B_SUB
        assert frontend._get_caller_sub(apigw_event_factory("/x", sub=None)) is None
        assert frontend._get_caller_sub({}) is None


# ============================================================
# handle_upload Tests
# ============================================================

class TestHandleUpload:
    def test_generates_presigned_url(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(USER_A_SUB)
        mock_s3.generate_presigned_url.return_value = "https://presigned.url/test"
        event = apigw_event_factory("/upload", body={
            "filename": "label.png",
            "contentType": "image/png",
            "region": "US_FDA",
            "projectId": "proj-1",
        })
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["uploadUrl"] == "https://presigned.url/test"
        assert body["region"] == "US_FDA"
        assert "label.png" in body["key"]

    def test_rejects_missing_content_type(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/upload", body={"filename": "test.png", "projectId": "proj-1"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_rejects_invalid_content_type(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/upload", body={
            "filename": "doc.pdf", "contentType": "application/pdf", "projectId": "proj-1"
        })
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400
        assert "JPEG and PNG" in json.loads(result["body"])["error"]

    def test_rejects_missing_project_id(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, _ = frontend_module
        event = apigw_event_factory("/upload", body={"filename": "label.png", "contentType": "image/png"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400
        mock_s3.generate_presigned_url.assert_not_called()

    def test_defaults_invalid_region_to_us_fda(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(USER_A_SUB)
        mock_s3.generate_presigned_url.return_value = "https://url"
        event = apigw_event_factory("/upload", body={
            "filename": "label.png", "contentType": "image/png", "region": "INVALID", "projectId": "proj-1"
        })
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["region"] == "US_FDA"

    def test_tagging_carries_region_and_project(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(USER_A_SUB)
        mock_s3.generate_presigned_url.return_value = "https://url"
        event = apigw_event_factory("/upload", body={
            "filename": "label.png", "contentType": "image/png", "region": "UK_MHRA", "projectId": "proj-1"
        })
        frontend.lambda_handler(event, None)
        tagging = mock_s3.generate_presigned_url.call_args.kwargs["Params"]["Tagging"]
        assert parse_qs(tagging) == {"regulatory_region": ["UK_MHRA"], "project_id": ["proj-1"]}

    def test_upload_key_is_grouped_under_project(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(USER_A_SUB)
        mock_s3.generate_presigned_url.return_value = "https://url"
        event = apigw_event_factory("/upload", body={
            "filename": "../label.png", "contentType": "image/png", "region": "US_FDA", "projectId": "proj-1"
        })
        body = json.loads(frontend.lambda_handler(event, None)["body"])
        assert body["key"].startswith("labels/US_FDA/proj-1/")
        assert body["key"].endswith("_label.png")

    @pytest.mark.parametrize("bad_id", [
        "proj-1&regulatory_region=UK_MHRA", "../other", "a/b", "x" * 65, "", 123, None,
    ])
    def test_rejects_unsafe_project_id(self, frontend_module, apigw_event_factory, bad_id):
        """Project IDs become part of S3 keys and tags, so only [A-Za-z0-9-] is accepted."""
        frontend, mock_s3, mock_table = frontend_module
        event = apigw_event_factory("/upload", body={
            "filename": "label.png", "contentType": "image/png", "projectId": bad_id
        })
        assert frontend.lambda_handler(event, None)["statusCode"] == 400
        mock_table.get_item.assert_not_called()
        mock_s3.generate_presigned_url.assert_not_called()


# ============================================================
# handle_check Tests
# ============================================================

class TestHandleCheck:
    def test_returns_completed_from_dynamodb(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_s3.generate_presigned_url.return_value = "https://presigned/annotated-001.png"
        mock_table.get_item.return_value = owned_by(
            USER_A_SUB,
            status="complete",
            annotatedKey="annotated-001.png",
            annotatedImageUrl="https://d123.cloudfront.net/annotated-001.png",  # legacy public URL
            complianceReport="The label has issues",
            formattedViolations=[{"title": "V1"}],
            progress={"step1": True, "step2": True, "step3": True},
        )
        event = apigw_event_factory("/check", body={"projectId": "proj-1"})
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["status"] == "completed"
        # A fresh presigned URL, never the stored public URL.
        assert body["annotatedImageUrl"] == "https://presigned/annotated-001.png"
        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "amzn-s3-demo-destination-bucket", "Key": "annotated-001.png"},
            ExpiresIn=3600,
        )

    def test_returns_processing_from_dynamodb(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(
            USER_A_SUB,
            status="processing",
            progress={"step1": True, "step2": False, "step3": False},
        )
        event = apigw_event_factory("/check", body={"projectId": "proj-1"})
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["status"] == "processing"
        assert body["progress"]["step1"] is True

    def test_rejects_missing_project_id(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, _ = frontend_module
        event = apigw_event_factory("/check", body={"key": "labels/US_FDA/x.png"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400
        # The old S3 lookup by image key (which had no ownership check) is gone.
        mock_s3.list_objects_v2.assert_not_called()
        mock_s3.get_object.assert_not_called()

    def test_returns_404_for_unknown_project(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.get_item.return_value = {}
        event = apigw_event_factory("/check", body={"projectId": "missing"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 404


# ============================================================
# Projects CRUD Tests
# ============================================================

class TestHandleProjectsList:
    def test_filters_scan_to_caller(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.scan.return_value = {"Items": []}
        frontend.lambda_handler(apigw_event_factory("/projects/list", sub=USER_B_SUB), None)
        kwargs = mock_table.scan.call_args.kwargs
        assert kwargs["ConsistentRead"] is True
        expr = kwargs["FilterExpression"].get_expression()
        assert expr["operator"] == "="
        assert expr["values"][0].name == "ownerSub"
        assert expr["values"][1] == USER_B_SUB

    def test_returns_presigned_urls_for_project_and_evaluations(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_s3.generate_presigned_url.side_effect = lambda op, Params, ExpiresIn: f"https://signed/{Params['Key']}"
        mock_table.scan.return_value = {"Items": [{
            "projectId": "p1", "ownerSub": USER_A_SUB,
            "annotatedKey": "annotated-new.png",
            "annotatedImageUrl": "https://d123.cloudfront.net/annotated-stale.png",
            "evaluations": [
                {"id": "e2", "annotatedKey": "annotated-new.png"},
                {"id": "e1", "annotatedImageUrl": "https://d123.cloudfront.net/annotated-old.png"},  # legacy
                {"id": "e0", "annotatedImageUrl": "https://d123.cloudfront.net/compliance-report-x.json"},
            ],
        }]}
        project = json.loads(frontend.lambda_handler(apigw_event_factory("/projects/list"), None)["body"])[0]
        assert project["annotatedImageUrl"] == "https://signed/annotated-new.png"
        assert [e["annotatedImageUrl"] for e in project["evaluations"]] == [
            "https://signed/annotated-new.png", "https://signed/annotated-old.png", "",
        ]
        assert "cloudfront" not in json.dumps(project)

    def test_project_without_image_has_no_image_url(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.scan.return_value = {"Items": [{
            "projectId": "p1", "ownerSub": USER_A_SUB, "annotatedImageUrl": "https://evil.example/x.png",
        }]}
        project = json.loads(frontend.lambda_handler(apigw_event_factory("/projects/list"), None)["body"])[0]
        assert "annotatedImageUrl" not in project
        mock_s3.generate_presigned_url.assert_not_called()

    def test_paginates_with_same_filter(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.scan.side_effect = [
            {"Items": [{"projectId": "p1", "ownerSub": USER_A_SUB}], "LastEvaluatedKey": {"projectId": "p1"}},
            {"Items": [{"projectId": "p2", "ownerSub": USER_A_SUB}]},
        ]
        result = frontend.lambda_handler(apigw_event_factory("/projects/list"), None)
        assert [p["projectId"] for p in json.loads(result["body"])] == ["p1", "p2"]
        second = mock_table.scan.call_args_list[1].kwargs
        assert second["ExclusiveStartKey"] == {"projectId": "p1"}
        assert second["FilterExpression"].get_expression()["values"][1] == USER_A_SUB


class TestHandleProjectsSave:
    def test_saves_project(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        event = apigw_event_factory("/projects/save", body={
            "project": {"id": "proj-1", "name": "Test Project", "region": "US_FDA"}
        })
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["saved"] == "proj-1"
        mock_table.update_item.assert_called_once()

    def test_save_is_conditional_on_ownership(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        event = apigw_event_factory("/projects/save", body={"project": {"id": "proj-1", "name": "X"}})
        frontend.lambda_handler(event, None)
        kwargs = mock_table.update_item.call_args.kwargs
        assert kwargs["Key"] == {"projectId": "proj-1"}
        assert kwargs["ConditionExpression"] == "attribute_not_exists(projectId) OR #owner = :owner"
        assert kwargs["ExpressionAttributeNames"]["#owner"] == "ownerSub"
        assert kwargs["ExpressionAttributeValues"][":owner"] == USER_A_SUB
        assert "#owner = :owner" in kwargs["UpdateExpression"]

    def test_client_cannot_set_server_owned_fields(self, frontend_module, apigw_event_factory):
        """S3 keys and image URLs are written only by the pipeline, so a client
        cannot point its own project at another user's objects."""
        frontend, _, mock_table = frontend_module
        event = apigw_event_factory("/projects/save", body={"project": {
            "id": "proj-1",
            "name": "Mine",
            "annotatedKey": "annotated-of-another-user.png",
            "reportKey": "compliance-report-x.json",
            "validationKey": "validation-x.json",
            "imageKey": "labels/US_FDA/other/x.png",
            "annotatedImageUrl": "https://evil.example/x.png",
            "evaluations": [{"annotatedKey": "annotated-of-another-user.png"}],
        }})
        frontend.lambda_handler(event, None)
        written = [v for k, v in mock_table.update_item.call_args.kwargs["ExpressionAttributeNames"].items()
                   if k != "#owner"]
        assert written == ["name"]

    def test_client_cannot_set_owner_or_key(self, frontend_module, apigw_event_factory):
        """ownerSub and projectId in the body are ignored; the owner comes from the token."""
        frontend, _, mock_table = frontend_module
        event = apigw_event_factory("/projects/save", sub=USER_B_SUB, body={
            "project": {"id": "proj-1", "name": "X", "ownerSub": USER_A_SUB, "projectId": "other"}
        })
        frontend.lambda_handler(event, None)
        kwargs = mock_table.update_item.call_args.kwargs
        assert kwargs["Key"] == {"projectId": "proj-1"}
        assert kwargs["ExpressionAttributeValues"][":owner"] == USER_B_SUB
        assert USER_A_SUB not in kwargs["ExpressionAttributeValues"].values()
        user_fields = [v for k, v in kwargs["ExpressionAttributeNames"].items() if k != "#owner"]
        assert user_fields == ["name"]

    def test_returns_404_when_project_owned_by_another_user(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.update_item.side_effect = conditional_check_failed("UpdateItem")
        event = apigw_event_factory("/projects/save", sub=USER_B_SUB, body={
            "project": {"id": "proj-1", "name": "Hijacked"}
        })
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 404

    def test_other_dynamodb_errors_return_500(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException"}}, "UpdateItem"
        )
        event = apigw_event_factory("/projects/save", body={"project": {"id": "proj-1", "name": "X"}})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 500

    def test_rejects_missing_project(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/projects/save", body={})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_rejects_missing_id(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/projects/save", body={"project": {"name": "No ID"}})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_handles_empty_item_after_id_pop(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        event = apigw_event_factory("/projects/save", body={"project": {"id": "proj-1"}})
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["saved"] == "proj-1"
        # No write, so an ID-only save cannot create a stub record or change anyone's project.
        mock_table.update_item.assert_not_called()

    def test_id_only_save_ignores_client_owner_field(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        event = apigw_event_factory("/projects/save", sub=USER_B_SUB, body={
            "project": {"id": "proj-1", "ownerSub": USER_B_SUB}
        })
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 200
        mock_table.update_item.assert_not_called()


class TestHandleProjectsDelete:
    def test_deletes_project(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.delete_item.return_value = {}
        event = apigw_event_factory("/projects/delete", body={"id": "proj-1"})
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["deleted"] == "proj-1"
        mock_table.delete_item.assert_called_once_with(
            Key={"projectId": "proj-1"},
            ConditionExpression="#owner = :owner",
            ExpressionAttributeNames={"#owner": "ownerSub"},
            ExpressionAttributeValues={":owner": USER_A_SUB},
            ReturnValues="ALL_OLD",
        )

    def test_cleanup_failure_does_not_fail_delete(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.delete_item.return_value = {"Attributes": {"annotatedKey": "annotated-1.png"}}
        mock_s3.delete_objects.side_effect = Exception("throttled")
        event = apigw_event_factory("/projects/delete", body={"id": "proj-1"})
        assert frontend.lambda_handler(event, None)["statusCode"] == 200

    def test_cross_user_delete_touches_no_objects(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.delete_item.side_effect = conditional_check_failed("DeleteItem")
        event = apigw_event_factory("/projects/delete", sub=USER_B_SUB, body={"id": "proj-1"})
        assert frontend.lambda_handler(event, None)["statusCode"] == 404
        mock_s3.delete_objects.assert_not_called()
        mock_s3.get_paginator.assert_not_called()

    def test_returns_404_when_project_owned_by_another_user(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.delete_item.side_effect = conditional_check_failed("DeleteItem")
        event = apigw_event_factory("/projects/delete", sub=USER_B_SUB, body={"id": "proj-1"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 404

    def test_rejects_missing_id(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/projects/delete", body={})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400


# ============================================================
# Cross-user access (user B targets user A's project)
# ============================================================

class TestCrossUserAccess:
    def test_check_on_other_users_project_returns_404_without_data(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(
            USER_A_SUB, status="complete", complianceReport="SECRET REPORT",
            annotatedImageUrl="https://d123.cloudfront.net/secret.png",
        )
        event = apigw_event_factory("/check", sub=USER_B_SUB, body={"projectId": "proj-1"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 404
        assert "SECRET" not in result["body"]
        assert "secret.png" not in result["body"]

    def test_upload_into_other_users_project_is_refused(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(USER_A_SUB)
        event = apigw_event_factory("/upload", sub=USER_B_SUB, body={
            "filename": "label.png", "contentType": "image/png", "projectId": "proj-1"
        })
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 404
        mock_s3.generate_presigned_url.assert_not_called()

    def test_upload_into_unknown_project_is_refused(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.get_item.return_value = {}
        event = apigw_event_factory("/upload", body={
            "filename": "label.png", "contentType": "image/png", "projectId": "does-not-exist"
        })
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 404
        mock_s3.generate_presigned_url.assert_not_called()

    def test_legacy_project_without_owner_is_not_accessible(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, mock_table = frontend_module
        mock_table.get_item.return_value = {"Item": {"projectId": "proj-1", "status": "complete"}}
        check = frontend.lambda_handler(
            apigw_event_factory("/check", body={"projectId": "proj-1"}), None
        )
        upload = frontend.lambda_handler(apigw_event_factory("/upload", body={
            "filename": "label.png", "contentType": "image/png", "projectId": "proj-1"
        }), None)
        assert check["statusCode"] == 404
        assert upload["statusCode"] == 404
        mock_s3.generate_presigned_url.assert_not_called()


# ============================================================
# Pure Helper Tests
# ============================================================

class TestImageUrlHelpers:
    @pytest.mark.parametrize("key", [
        "compliance-report-1.json", "validation-1.json", "labels/US_FDA/p/x.png",
        "annotated-1.png/../secret", "nested/annotated-1.png", "annotated-1.jpg", None, 5,
    ])
    def test_only_annotated_images_are_presigned(self, frontend_module, key):
        frontend, mock_s3, _ = frontend_module
        assert frontend._annotated_image_url(key) == ""
        mock_s3.generate_presigned_url.assert_not_called()

    def test_legacy_key_from_cloudfront_url(self, frontend_module):
        frontend, _, _ = frontend_module
        assert frontend._legacy_annotated_key("https://d1.cloudfront.net/annotated-20260101_1-ab.png") \
            == "annotated-20260101_1-ab.png"
        assert frontend._legacy_annotated_key("https://d1.cloudfront.net/x/annotated-1.png") is None
        assert frontend._legacy_annotated_key(None) is None


class TestDenialLogging:
    def test_cross_user_denial_logs_caller_sub(self, frontend_module, apigw_event_factory, caplog):
        frontend, _, mock_table = frontend_module
        mock_table.get_item.return_value = owned_by(USER_A_SUB)
        with caplog.at_level("WARNING"):
            frontend.lambda_handler(apigw_event_factory("/check", sub=USER_B_SUB, body={"projectId": "proj-1"}), None)
        assert any(USER_B_SUB in r.getMessage() and "proj-1" in r.getMessage() for r in caplog.records)


class TestSanitizeFilename:
    def test_strips_path_separators(self, frontend_module):
        frontend, _, _ = frontend_module
        assert frontend._sanitize_filename("../../etc/passwd") == "passwd"

    def test_replaces_unsafe_chars(self, frontend_module):
        frontend, _, _ = frontend_module
        result = frontend._sanitize_filename("file<>name.jpg")
        assert "<" not in result
        assert ">" not in result
        assert result == "file__name.jpg"

    def test_truncates_to_255_chars(self, frontend_module):
        frontend, _, _ = frontend_module
        long_name = "a" * 300 + ".png"
        result = frontend._sanitize_filename(long_name)
        assert len(result) <= 255

    def test_empty_string_returns_upload(self, frontend_module):
        frontend, _, _ = frontend_module
        assert frontend._sanitize_filename("") == "upload"

    def test_backslash_paths(self, frontend_module):
        frontend, _, _ = frontend_module
        assert frontend._sanitize_filename("C:\\Users\\file.jpg") == "file.jpg"


class TestConvertFloats:
    def test_converts_float_to_decimal(self, frontend_module):
        frontend, _, _ = frontend_module
        result = frontend._convert_floats(3.14)
        assert isinstance(result, Decimal)

    def test_handles_nested_dicts(self, frontend_module):
        frontend, _, _ = frontend_module
        result = frontend._convert_floats({"score": 0.95, "name": "test"})
        assert isinstance(result["score"], Decimal)
        assert result["name"] == "test"

    def test_handles_nested_lists(self, frontend_module):
        frontend, _, _ = frontend_module
        result = frontend._convert_floats([1.0, 2.0, "text"])
        assert isinstance(result[0], Decimal)
        assert result[2] == "text"

    def test_leaves_non_floats_alone(self, frontend_module):
        frontend, _, _ = frontend_module
        assert frontend._convert_floats(42) == 42
        assert frontend._convert_floats("hello") == "hello"
        assert frontend._convert_floats(None) is None


class TestDecimalEncoder:
    def test_integer_decimal_becomes_int(self, frontend_module):
        frontend, _, _ = frontend_module
        result = json.dumps({"val": Decimal("5")}, cls=frontend.DecimalEncoder)
        assert json.loads(result)["val"] == 5

    def test_fractional_decimal_becomes_float(self, frontend_module):
        frontend, _, _ = frontend_module
        result = json.dumps({"val": Decimal("3.14")}, cls=frontend.DecimalEncoder)
        assert abs(json.loads(result)["val"] - 3.14) < 0.001
