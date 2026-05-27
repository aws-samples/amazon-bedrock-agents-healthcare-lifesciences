"""Unit tests for the frontend API Lambda function."""

import json
import os
import sys
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def frontend_env(monkeypatch):
    monkeypatch.setenv("INCOMING_BUCKET", "pharmalabel-incoming-test")
    monkeypatch.setenv("RESULTS_BUCKET", "pharmalabel-results-test")
    monkeypatch.setenv("CLOUDFRONT_URL", "https://d123.cloudfront.net")
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

        frontend.s3 = mock_s3_client.return_value
        frontend.projects_table = mock_table
        yield frontend, mock_s3_client.return_value, mock_table


# ============================================================
# Request Routing Tests
# ============================================================

class TestRequestRouting:
    def test_routes_to_upload(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, _ = frontend_module
        mock_s3.generate_presigned_url.return_value = "https://presigned.url"
        event = apigw_event_factory("/upload", body={"filename": "test.png", "contentType": "image/png"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_routes_to_check(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.get_item.return_value = {"Item": {"status": "processing", "progress": {}}}
        event = apigw_event_factory("/check", body={"projectId": "p1"})
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
        frontend, mock_s3, _ = frontend_module
        mock_s3.generate_presigned_url.side_effect = Exception("boom")
        event = apigw_event_factory("/upload", body={"filename": "test.png", "contentType": "image/png"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 500


# ============================================================
# handle_upload Tests
# ============================================================

class TestHandleUpload:
    def test_generates_presigned_url(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, _ = frontend_module
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
        event = apigw_event_factory("/upload", body={"filename": "test.png"})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_rejects_invalid_content_type(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/upload", body={
            "filename": "doc.pdf", "contentType": "application/pdf"
        })
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400
        assert "JPEG and PNG" in json.loads(result["body"])["error"]

    def test_defaults_invalid_region_to_us_fda(self, frontend_module, apigw_event_factory):
        frontend, mock_s3, _ = frontend_module
        mock_s3.generate_presigned_url.return_value = "https://url"
        event = apigw_event_factory("/upload", body={
            "filename": "label.png", "contentType": "image/png", "region": "INVALID"
        })
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["region"] == "US_FDA"


# ============================================================
# handle_check Tests
# ============================================================

class TestHandleCheck:
    def test_returns_completed_from_dynamodb(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.get_item.return_value = {
            "Item": {
                "status": "complete",
                "annotatedImageUrl": "https://d123.cloudfront.net/annotated.png",
                "complianceReport": "The label has issues",
                "formattedViolations": [{"title": "V1"}],
                "progress": {"step1": True, "step2": True, "step3": True},
            }
        }
        event = apigw_event_factory("/check", body={"projectId": "proj-1"})
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["status"] == "completed"
        assert body["annotatedImageUrl"] == "https://d123.cloudfront.net/annotated.png"

    def test_returns_processing_from_dynamodb(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        mock_table.get_item.return_value = {
            "Item": {
                "status": "processing",
                "progress": {"step1": True, "step2": False, "step3": False},
            }
        }
        event = apigw_event_factory("/check", body={"projectId": "proj-1"})
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["status"] == "processing"
        assert body["progress"]["step1"] is True

    def test_fallback_to_processing_when_no_project_id_or_key(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/check", body={})
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["status"] == "processing"


# ============================================================
# Projects CRUD Tests
# ============================================================

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
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/projects/save", body={"project": {"id": "proj-1"}})
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["saved"] == "proj-1"


class TestHandleProjectsDelete:
    def test_deletes_project(self, frontend_module, apigw_event_factory):
        frontend, _, mock_table = frontend_module
        event = apigw_event_factory("/projects/delete", body={"id": "proj-1"})
        result = frontend.lambda_handler(event, None)
        body = json.loads(result["body"])
        assert body["deleted"] == "proj-1"
        mock_table.delete_item.assert_called_once_with(Key={"projectId": "proj-1"})

    def test_rejects_missing_id(self, frontend_module, apigw_event_factory):
        frontend, _, _ = frontend_module
        event = apigw_event_factory("/projects/delete", body={})
        result = frontend.lambda_handler(event, None)
        assert result["statusCode"] == 400


# ============================================================
# Pure Helper Tests
# ============================================================

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
