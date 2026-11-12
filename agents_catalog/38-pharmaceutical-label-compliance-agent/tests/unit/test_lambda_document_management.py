"""Unit tests for the document management Lambda function."""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from tests.conftest import KB_ADMIN_GROUP, USER_A_SUB


@pytest.fixture(autouse=True)
def docmgmt_env(monkeypatch):
    monkeypatch.setenv("KB_BUCKET", "amzn-s3-demo-bucket2")
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "KB-TEST-123")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://d123.cloudfront.net")


@pytest.fixture
def docmgmt_module():
    """Import document_management/index.py with mocked boto3."""
    with patch("boto3.client") as mock_boto3_client:
        mock_s3 = MagicMock()
        mock_bedrock = MagicMock()

        def client_factory(service, **kwargs):
            if service == "s3":
                return mock_s3
            return mock_bedrock

        mock_boto3_client.side_effect = client_factory

        docmgmt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "lambda_functions", "document_management"
        )
        sys.path.insert(0, docmgmt_path)
        if "index" in sys.modules:
            del sys.modules["index"]
        import index as docmgmt
        sys.path.pop(0)

        docmgmt.amazon_s3 = mock_s3
        docmgmt.amazon_bedrock_agent = mock_bedrock
        docmgmt._ds_id_cache.clear()
        yield docmgmt, mock_s3, mock_bedrock


# ============================================================
# Routing Tests
# ============================================================

class TestDocMgmtRouting:
    def test_routes_to_list(self, docmgmt_module, apigw_event_factory):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.list_objects_v2.return_value = {"Contents": [], "IsTruncated": False}
        event = apigw_event_factory("/documents/list")
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_routes_to_upload(self, docmgmt_module, apigw_event_factory):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.generate_presigned_url.return_value = "https://presigned"
        event = apigw_event_factory("/documents/upload", groups=[KB_ADMIN_GROUP], body={
            "region": "US_FDA", "filename": "test.pdf", "contentType": "application/pdf"
        })
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_invalid_json_returns_400(self, docmgmt_module, apigw_event_factory):
        docmgmt, _, _ = docmgmt_module
        event = apigw_event_factory("/documents/list", raw_body="{not json")
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_returns_404_for_unknown_path(self, docmgmt_module, apigw_event_factory):
        docmgmt, _, _ = docmgmt_module
        event = apigw_event_factory("/documents/nonexistent")
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 404

    def test_options_returns_cors_headers(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        event = {
            "rawPath": "/documents/list",
            "requestContext": {"http": {"method": "OPTIONS"}},
            "headers": {},
            "body": "",
        }
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]


# ============================================================
# Authorization Tests (identity + kb-admins role gate)
# ============================================================

ADMIN_ROUTE_BODIES = {
    "/documents/upload": {"region": "US_FDA", "filename": "fake.pdf", "contentType": "application/pdf"},
    "/documents/delete": {"region": "US_FDA", "key": "US_FDA/real.pdf"},
    "/documents/sync": {"region": "US_FDA"},
}


class TestKnowledgeBaseAuthorization:
    @pytest.mark.parametrize("path", [
        "/documents/list", "/documents/download", *ADMIN_ROUTE_BODIES,
    ])
    def test_rejects_request_without_verified_identity(self, docmgmt_module, apigw_event_factory, path):
        docmgmt, mock_s3, mock_bedrock = docmgmt_module
        event = apigw_event_factory(path, body={"region": "US_FDA", "key": "US_FDA/a.pdf"}, sub=None)
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 401
        mock_s3.list_objects_v2.assert_not_called()
        mock_s3.generate_presigned_url.assert_not_called()
        mock_s3.delete_object.assert_not_called()
        mock_bedrock.start_ingestion_job.assert_not_called()

    @pytest.mark.parametrize("path,body", list(ADMIN_ROUTE_BODIES.items()))
    def test_non_admin_cannot_change_knowledge_base(self, docmgmt_module, apigw_event_factory, path, body):
        docmgmt, mock_s3, mock_bedrock = docmgmt_module
        event = apigw_event_factory(path, body=body, groups=["some-other-group"])
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 403
        assert "administrators" in json.loads(result["body"])["error"]
        # The handler never reached S3 or Bedrock.
        mock_s3.head_object.assert_not_called()
        mock_s3.generate_presigned_url.assert_not_called()
        mock_s3.delete_object.assert_not_called()
        mock_bedrock.start_ingestion_job.assert_not_called()

    @pytest.mark.parametrize("path", list(ADMIN_ROUTE_BODIES))
    def test_user_with_no_groups_cannot_change_knowledge_base(self, docmgmt_module, apigw_event_factory, path):
        docmgmt, _, _ = docmgmt_module
        event = apigw_event_factory(path, body=ADMIN_ROUTE_BODIES[path], groups=None)
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 403

    def test_admin_can_delete(self, docmgmt_module, apigw_event_factory):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.head_object.return_value = {}
        mock_s3.exceptions.ClientError = ClientError
        event = apigw_event_factory("/documents/delete", groups=[KB_ADMIN_GROUP],
                                    body=ADMIN_ROUTE_BODIES["/documents/delete"])
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 200
        mock_s3.delete_object.assert_called_once()

    def test_admin_can_sync(self, docmgmt_module, apigw_event_factory):
        docmgmt, _, mock_bedrock = docmgmt_module
        mock_bedrock.list_data_sources.return_value = {
            "dataSourceSummaries": [{"name": "US-FDA-Regulatory-Documents", "dataSourceId": "ds-1"}]
        }
        mock_bedrock.start_ingestion_job.return_value = {"ingestionJob": {"ingestionJobId": "j1"}}
        event = apigw_event_factory("/documents/sync", groups=["other", KB_ADMIN_GROUP],
                                    body={"region": "US_FDA"})
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 200
        mock_bedrock.start_ingestion_job.assert_called_once()

    def test_non_admin_can_list(self, docmgmt_module, apigw_event_factory):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.list_objects_v2.return_value = {"Contents": [], "IsTruncated": False}
        result = docmgmt.lambda_handler(apigw_event_factory("/documents/list"), None)
        assert result["statusCode"] == 200

    def test_non_admin_can_download(self, docmgmt_module, apigw_event_factory):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.head_object.return_value = {}
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.generate_presigned_url.return_value = "https://download.url"
        event = apigw_event_factory("/documents/download", body={"region": "US_FDA", "key": "US_FDA/a.pdf"})
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_group_name_must_match_exactly(self, docmgmt_module, apigw_event_factory):
        docmgmt, _, _ = docmgmt_module
        event = apigw_event_factory("/documents/sync", groups=["kb-admins-readonly", "not-kb-admins"],
                                    body={"region": "US_FDA"})
        result = docmgmt.lambda_handler(event, None)
        assert result["statusCode"] == 403

    @pytest.mark.parametrize("raw_groups,expected", [
        ("[kb-admins]", {"kb-admins"}),
        ("[viewers kb-admins]", {"viewers", "kb-admins"}),
        ('["viewers","kb-admins"]', {"viewers", "kb-admins"}),
        (["kb-admins", "viewers"], {"kb-admins", "viewers"}),
        ("", set()),
        ("[]", set()),
    ])
    def test_parses_cognito_groups_claim_formats(self, docmgmt_module, raw_groups, expected):
        docmgmt, _, _ = docmgmt_module
        event = {"requestContext": {"authorizer": {"jwt": {"claims": {
            "sub": USER_A_SUB, "cognito:groups": raw_groups,
        }}}}}
        assert docmgmt._get_caller(event) == (USER_A_SUB, expected)

    def test_admin_group_is_configurable(self, docmgmt_module, apigw_event_factory, monkeypatch):
        docmgmt, _, _ = docmgmt_module
        monkeypatch.setattr(docmgmt, "KB_ADMIN_GROUP", "regulatory-editors")
        event = apigw_event_factory("/documents/sync", groups=[KB_ADMIN_GROUP], body={"region": "US_FDA"})
        assert docmgmt.lambda_handler(event, None)["statusCode"] == 403


# ============================================================
# handle_list Tests
# ============================================================

class TestHandleList:
    def test_lists_documents_for_specific_region(self, docmgmt_module):
        docmgmt, mock_s3, _ = docmgmt_module
        from datetime import datetime
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "US_FDA/doc1.pdf", "Size": 1024, "LastModified": datetime(2024, 1, 1)},
                {"Key": "US_FDA/doc2.pdf", "Size": 2048, "LastModified": datetime(2024, 1, 2)},
            ],
            "IsTruncated": False,
        }
        result = docmgmt.handle_list({"region": "US_FDA"})
        body = json.loads(result["body"])
        assert "US_FDA" in body
        assert len(body["US_FDA"]["documents"]) == 2
        assert "UK_MHRA" not in body

    def test_lists_all_regions_when_none_specified(self, docmgmt_module):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.list_objects_v2.return_value = {"Contents": [], "IsTruncated": False}
        result = docmgmt.handle_list({})
        body = json.loads(result["body"])
        assert "US_FDA" in body
        assert "UK_MHRA" in body

    def test_skips_directory_keys(self, docmgmt_module):
        docmgmt, mock_s3, _ = docmgmt_module
        from datetime import datetime
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "US_FDA/", "Size": 0, "LastModified": datetime(2024, 1, 1)},
                {"Key": "US_FDA/real.pdf", "Size": 100, "LastModified": datetime(2024, 1, 1)},
            ],
            "IsTruncated": False,
        }
        result = docmgmt.handle_list({"region": "US_FDA"})
        body = json.loads(result["body"])
        assert len(body["US_FDA"]["documents"]) == 1
        assert body["US_FDA"]["documents"][0]["name"] == "real.pdf"


# ============================================================
# handle_upload Tests
# ============================================================

class TestHandleUpload:
    def test_generates_presigned_url(self, docmgmt_module):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.generate_presigned_url.return_value = "https://upload.url"
        result = docmgmt.handle_upload({
            "region": "US_FDA", "filename": "regs.pdf", "contentType": "application/pdf"
        })
        body = json.loads(result["body"])
        assert body["uploadUrl"] == "https://upload.url"
        assert body["key"] == "US_FDA/regs.pdf"

    def test_rejects_invalid_region(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt.handle_upload({
            "region": "INVALID", "filename": "test.pdf", "contentType": "application/pdf"
        })
        assert result["statusCode"] == 400

    def test_rejects_invalid_content_type_for_upload(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt.handle_upload({
            "region": "US_FDA", "filename": "img.png", "contentType": "image/png"
        })
        assert result["statusCode"] == 400

    def test_rejects_invalid_content_type(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt.handle_upload({
            "region": "US_FDA", "filename": "image.png", "contentType": "image/png"
        })
        assert result["statusCode"] == 400

    def test_rejects_existing_file_409(self, docmgmt_module):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.head_object.return_value = {}  # File exists
        mock_s3.exceptions.ClientError = ClientError
        result = docmgmt.handle_upload({
            "region": "US_FDA", "filename": "existing.pdf", "contentType": "application/pdf"
        })
        assert result["statusCode"] == 409


# ============================================================
# handle_delete Tests
# ============================================================

class TestHandleDelete:
    def test_deletes_document(self, docmgmt_module):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.head_object.return_value = {}
        mock_s3.exceptions.ClientError = ClientError
        result = docmgmt.handle_delete({"key": "US_FDA/doc.pdf", "region": "US_FDA"})
        body = json.loads(result["body"])
        assert body["deleted"] == "US_FDA/doc.pdf"
        mock_s3.delete_object.assert_called_once()

    def test_rejects_missing_key(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt.handle_delete({"region": "US_FDA"})
        assert result["statusCode"] == 400

    def test_rejects_invalid_region(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt.handle_delete({"key": "US_FDA/doc.pdf", "region": "INVALID"})
        assert result["statusCode"] == 400

    def test_rejects_key_not_in_region_prefix(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt.handle_delete({"key": "UK_MHRA/doc.pdf", "region": "US_FDA"})
        assert result["statusCode"] == 403

    def test_returns_404_for_nonexistent_file(self, docmgmt_module):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_s3.exceptions.ClientError = ClientError
        result = docmgmt.handle_delete({"key": "US_FDA/missing.pdf", "region": "US_FDA"})
        assert result["statusCode"] == 404


# ============================================================
# handle_download Tests
# ============================================================

class TestHandleDownload:
    def test_generates_download_url(self, docmgmt_module):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.head_object.return_value = {}
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.generate_presigned_url.return_value = "https://download.url"
        result = docmgmt.handle_download({"key": "US_FDA/doc.pdf", "region": "US_FDA"})
        body = json.loads(result["body"])
        assert body["downloadUrl"] == "https://download.url"

    def test_rejects_key_not_in_region(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt.handle_download({"key": "UK_MHRA/doc.pdf", "region": "US_FDA"})
        assert result["statusCode"] == 403

    def test_returns_404_for_nonexistent_file(self, docmgmt_module):
        docmgmt, mock_s3, _ = docmgmt_module
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_s3.exceptions.ClientError = ClientError
        result = docmgmt.handle_download({"key": "US_FDA/missing.pdf", "region": "US_FDA"})
        assert result["statusCode"] == 404


# ============================================================
# handle_sync Tests
# ============================================================

class TestHandleSync:
    def test_starts_ingestion_job(self, docmgmt_module):
        docmgmt, _, mock_bedrock = docmgmt_module
        mock_bedrock.list_data_sources.return_value = {
            "dataSourceSummaries": [
                {"name": "US-FDA-Regulatory-Documents", "dataSourceId": "ds-123"}
            ]
        }
        mock_bedrock.start_ingestion_job.return_value = {
            "ingestionJob": {"ingestionJobId": "job-456", "status": "STARTING"}
        }
        result = docmgmt.handle_sync({"region": "US_FDA"})
        body = json.loads(result["body"])
        assert body["ingestionJobId"] == "job-456"
        assert body["status"] == "STARTING"

    def test_rejects_invalid_region(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt.handle_sync({"region": "INVALID"})
        assert result["statusCode"] == 400


# ============================================================
# Pure Helper Tests
# ============================================================

class TestSanitizeFilenameDocMgmt:
    def test_strips_path_separators(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        assert docmgmt._sanitize_filename("../../etc/passwd") == "passwd"

    def test_replaces_unsafe_chars(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt._sanitize_filename("file (copy).pdf")
        assert "(" not in result
        assert " " not in result

    def test_empty_returns_upload(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        assert docmgmt._sanitize_filename("") == "upload"


class TestResponseHelper:
    def test_builds_response_with_headers(self, docmgmt_module):
        docmgmt, _, _ = docmgmt_module
        result = docmgmt.response(200, {"key": "value"})
        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]
        assert json.loads(result["body"]) == {"key": "value"}
