"""Integration tests for document management Lambda with moto S3."""

import json
import os
import sys
import pytest
from moto import mock_aws
import boto3

from tests.conftest import KB_ADMIN_GROUP, USER_A_SUB, make_apigw_event


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    # Placeholder credentials; moto intercepts AWS calls and only needs them set.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "ACCESS_KEY_ID_EXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "SECRET_ACCESS_KEY_EXAMPLE")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "SECURITY_TOKEN_EXAMPLE")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "SESSION_TOKEN_EXAMPLE")
    monkeypatch.setenv("KB_BUCKET", "amzn-s3-demo-bucket2")
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "KB-TEST-123")
    monkeypatch.setenv("FRONTEND_ORIGIN", "*")


@mock_aws
class TestDocumentLifecycle:
    def _setup_aws(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="amzn-s3-demo-bucket2")
        # Seed with some documents
        s3.put_object(Bucket="amzn-s3-demo-bucket2", Key="US_FDA/existing_doc.pdf", Body=b"fake pdf")
        s3.put_object(Bucket="amzn-s3-demo-bucket2", Key="UK_MHRA/mhra_doc.pdf", Body=b"fake pdf 2")
        return s3

    def _import_handler(self):
        docmgmt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "lambda_functions", "document_management"
        )
        sys.path.insert(0, docmgmt_path)
        if "index" in sys.modules:
            del sys.modules["index"]
        import index as docmgmt
        sys.path.pop(0)
        return docmgmt

    def _make_event(self, path, body=None, groups=(KB_ADMIN_GROUP,)):
        # Defaults to a knowledge base administrator; pass groups=() for a regular user.
        return make_apigw_event(path, body=body or {}, sub=USER_A_SUB, groups=list(groups))

    def test_list_returns_seeded_documents(self, aws_env):
        self._setup_aws()
        docmgmt = self._import_handler()

        result = docmgmt.lambda_handler(self._make_event("/documents/list", {"region": "US_FDA"}), None)
        body = json.loads(result["body"])
        assert len(body["US_FDA"]["documents"]) == 1
        assert body["US_FDA"]["documents"][0]["name"] == "existing_doc.pdf"

    def test_list_all_regions(self, aws_env):
        self._setup_aws()
        docmgmt = self._import_handler()

        result = docmgmt.lambda_handler(self._make_event("/documents/list", {}), None)
        body = json.loads(result["body"])
        assert "US_FDA" in body
        assert "UK_MHRA" in body
        assert len(body["US_FDA"]["documents"]) == 1
        assert len(body["UK_MHRA"]["documents"]) == 1

    def test_upload_generates_presigned_url_for_new_file(self, aws_env):
        self._setup_aws()
        docmgmt = self._import_handler()

        result = docmgmt.lambda_handler(self._make_event("/documents/upload", {
            "region": "US_FDA",
            "filename": "new_regulation.pdf",
            "contentType": "application/pdf",
        }), None)
        body = json.loads(result["body"])
        assert result["statusCode"] == 200
        assert "uploadUrl" in body
        assert body["key"] == "US_FDA/new_regulation.pdf"

    def test_upload_conflict_for_existing_file(self, aws_env):
        self._setup_aws()
        docmgmt = self._import_handler()

        result = docmgmt.lambda_handler(self._make_event("/documents/upload", {
            "region": "US_FDA",
            "filename": "existing_doc.pdf",
            "contentType": "application/pdf",
        }), None)
        assert result["statusCode"] == 409

    def test_delete_removes_document(self, aws_env):
        s3 = self._setup_aws()
        docmgmt = self._import_handler()

        # Delete
        result = docmgmt.lambda_handler(self._make_event("/documents/delete", {
            "key": "US_FDA/existing_doc.pdf",
            "region": "US_FDA",
        }), None)
        assert result["statusCode"] == 200

        # Verify gone
        list_result = docmgmt.lambda_handler(self._make_event("/documents/list", {"region": "US_FDA"}), None)
        body = json.loads(list_result["body"])
        assert len(body["US_FDA"]["documents"]) == 0

    def test_download_generates_presigned_url(self, aws_env):
        self._setup_aws()
        docmgmt = self._import_handler()

        result = docmgmt.lambda_handler(self._make_event("/documents/download", {
            "key": "US_FDA/existing_doc.pdf",
            "region": "US_FDA",
        }), None)
        body = json.loads(result["body"])
        assert result["statusCode"] == 200
        assert "downloadUrl" in body

    def test_delete_nonexistent_returns_404(self, aws_env):
        self._setup_aws()
        docmgmt = self._import_handler()

        result = docmgmt.lambda_handler(self._make_event("/documents/delete", {
            "key": "US_FDA/nonexistent.pdf",
            "region": "US_FDA",
        }), None)
        assert result["statusCode"] == 404

    # --- Regular (non-admin) users cannot change the shared knowledge base --- #

    def test_regular_user_cannot_delete_document(self, aws_env):
        s3 = self._setup_aws()
        docmgmt = self._import_handler()

        result = docmgmt.lambda_handler(self._make_event("/documents/delete", {
            "key": "US_FDA/existing_doc.pdf",
            "region": "US_FDA",
        }, groups=()), None)
        assert result["statusCode"] == 403

        # Document is still in the bucket.
        s3.head_object(Bucket="amzn-s3-demo-bucket2", Key="US_FDA/existing_doc.pdf")

    def test_regular_user_cannot_get_upload_url(self, aws_env):
        self._setup_aws()
        docmgmt = self._import_handler()

        result = docmgmt.lambda_handler(self._make_event("/documents/upload", {
            "region": "US_FDA",
            "filename": "poisoned_regulation.pdf",
            "contentType": "application/pdf",
        }, groups=()), None)
        assert result["statusCode"] == 403
        assert "uploadUrl" not in json.loads(result["body"])

    def test_regular_user_cannot_sync(self, aws_env):
        self._setup_aws()
        docmgmt = self._import_handler()

        result = docmgmt.lambda_handler(
            self._make_event("/documents/sync", {"region": "US_FDA"}, groups=()), None
        )
        assert result["statusCode"] == 403

    def test_regular_user_can_list_and_download(self, aws_env):
        self._setup_aws()
        docmgmt = self._import_handler()

        listed = docmgmt.lambda_handler(
            self._make_event("/documents/list", {"region": "US_FDA"}, groups=()), None
        )
        assert listed["statusCode"] == 200
        assert len(json.loads(listed["body"])["US_FDA"]["documents"]) == 1

        downloaded = docmgmt.lambda_handler(self._make_event("/documents/download", {
            "key": "US_FDA/existing_doc.pdf",
            "region": "US_FDA",
        }, groups=()), None)
        assert downloaded["statusCode"] == 200
