"""Unit tests for steering_hooks.py."""

import json
import pytest
from unittest.mock import patch, MagicMock

from steering_hooks import (
    ComplianceWorkflowPlugin,
    AnnotationWorkflowPlugin,
    ValidationWorkflowPlugin,
)


# ============================================================
# ComplianceWorkflowPlugin Tests
# ============================================================

class TestComplianceWorkflowPluginOrdering:
    """Tests for tool call ordering enforcement."""

    def test_blocks_store_without_retrieve(self, before_event, sample_violations_json):
        plugin = ComplianceWorkflowPlugin()
        event = before_event("store_compliance_report", {
            "violations": sample_violations_json,
            "report": "some report",
            "source_file": "test.png",
        })
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is not None
        assert "retrieve" in event.cancel_tool

    def test_allows_store_after_retrieve(self, before_event, after_event, sample_violations_json):
        plugin = ComplianceWorkflowPlugin()
        plugin.track_tool_calls(after_event("retrieve", result="some KB result"))

        event = before_event("store_compliance_report", {
            "violations": sample_violations_json,
            "report": "some report",
            "source_file": "test.png",
        })
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is None

    def test_allows_unrelated_tools_without_history(self, before_event):
        plugin = ComplianceWorkflowPlugin()
        event = before_event("some_other_tool", {"param": "value"})
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is None

    def test_failed_tool_not_tracked(self, after_event):
        plugin = ComplianceWorkflowPlugin()
        plugin.track_tool_calls(after_event("retrieve", result=Exception("failed")))
        assert "retrieve" not in plugin._tool_history


class TestComplianceWorkflowPluginViolationValidation:
    """Tests for violation JSON structure enforcement."""

    def _make_plugin_with_retrieve(self, after_event):
        plugin = ComplianceWorkflowPlugin()
        plugin.track_tool_calls(after_event("retrieve", result="ok"))
        return plugin

    def test_rejects_non_array_violations(self, before_event, after_event):
        plugin = self._make_plugin_with_retrieve(after_event)
        event = before_event("store_compliance_report", {
            "violations": '{"not": "array"}',
        })
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is not None
        assert "JSON array" in event.cancel_tool

    def test_rejects_invalid_json(self, before_event, after_event):
        plugin = self._make_plugin_with_retrieve(after_event)
        event = before_event("store_compliance_report", {
            "violations": "not json at all {{{",
        })
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is not None
        assert "valid JSON array" in event.cancel_tool

    def test_rejects_missing_required_fields(self, before_event, after_event):
        plugin = self._make_plugin_with_retrieve(after_event)
        violations = [{"title": "Missing header"}]  # missing description and severity
        event = before_event("store_compliance_report", {
            "violations": json.dumps(violations),
        })
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is not None
        assert "missing required fields" in event.cancel_tool

    def test_rejects_invalid_severity(self, before_event, after_event):
        plugin = self._make_plugin_with_retrieve(after_event)
        violations = [{"title": "X", "description": "Y", "severity": "critical"}]
        event = before_event("store_compliance_report", {
            "violations": json.dumps(violations),
        })
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is not None
        assert "invalid severity" in event.cancel_tool

    def test_accepts_valid_violations_all_severities(self, before_event, after_event):
        plugin = self._make_plugin_with_retrieve(after_event)
        for severity in ["high", "medium", "low"]:
            violations = [{"title": "X", "description": "Y", "severity": severity}]
            event = before_event("store_compliance_report", {
                "violations": json.dumps(violations),
            })
            plugin.enforce_workflow_and_structure(event)
            assert event.cancel_tool is None, f"Failed for severity={severity}"

    def test_accepts_empty_violations_array(self, before_event, after_event):
        plugin = self._make_plugin_with_retrieve(after_event)
        event = before_event("store_compliance_report", {
            "violations": "[]",
        })
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is None

    def test_violations_as_list_not_string(self, before_event, after_event):
        plugin = self._make_plugin_with_retrieve(after_event)
        violations = [{"title": "X", "description": "Y", "severity": "high"}]
        event = before_event("store_compliance_report", {
            "violations": violations,  # list, not JSON string
        })
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is None

    def test_rejects_severity_at_specific_index(self, before_event, after_event):
        plugin = self._make_plugin_with_retrieve(after_event)
        violations = [
            {"title": "A", "description": "B", "severity": "high"},
            {"title": "C", "description": "D", "severity": "INVALID"},
        ]
        event = before_event("store_compliance_report", {
            "violations": json.dumps(violations),
        })
        plugin.enforce_workflow_and_structure(event)
        assert event.cancel_tool is not None
        assert "index 1" in event.cancel_tool


# ============================================================
# AnnotationWorkflowPlugin Tests
# ============================================================

class TestAnnotationWorkflowPluginOrdering:
    """Tests for annotation tool ordering enforcement."""

    def test_blocks_get_text_regions_without_load_s3_data(self, before_event):
        plugin = AnnotationWorkflowPlugin()
        event = before_event("get_text_regions", {"image_bucket": "b", "image_key": "k"})
        plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "load_s3_data" in event.cancel_tool

    def test_blocks_draw_annotations_without_load_s3_data(self, before_event):
        plugin = AnnotationWorkflowPlugin()
        event = before_event("draw_annotations", {"annotations": []})
        plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "load_s3_data" in event.cancel_tool

    def test_blocks_draw_annotations_without_get_text_regions(self, before_event, after_event):
        plugin = AnnotationWorkflowPlugin()
        plugin.track_tool_calls(after_event("load_s3_data", result="ok"))
        event = before_event("draw_annotations", {"annotations": []})
        plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "get_text_regions" in event.cancel_tool

    def test_allows_correct_ordering(self, before_event, after_event, sample_annotations):
        plugin = AnnotationWorkflowPlugin()
        plugin._compliance_json_bucket = "test-bucket"
        plugin._compliance_json_key = "report.json"
        plugin.track_tool_calls(after_event("load_s3_data", result="ok"))
        plugin.track_tool_calls(after_event("get_text_regions", result="ok"))

        mock_s3_response = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps({
                "violations": [
                    {"title": "Missing Drug Facts header"},
                    {"title": "Unsubstantiated marketing claim"},
                    {"title": "Font size below minimum"},
                ]
            }).encode()))
        }

        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = mock_s3_response
            event = before_event("draw_annotations", {
                "image_bucket": "b",
                "image_key": "k",
                "annotations": sample_annotations,
            })
            plugin.enforce_annotation_rules(event)

        assert event.cancel_tool is None


class TestAnnotationWorkflowPluginCountValidation:
    """Tests for annotation count matching violation count."""

    def _setup_plugin(self, after_event):
        plugin = AnnotationWorkflowPlugin()
        plugin._compliance_json_bucket = "test-bucket"
        plugin._compliance_json_key = "report.json"
        plugin.track_tool_calls(after_event("load_s3_data", result="ok"))
        plugin.track_tool_calls(after_event("get_text_regions", result="ok"))
        return plugin

    def _mock_s3_violations(self, count):
        violations = [{"title": f"Violation {i}"} for i in range(count)]
        return {
            "Body": MagicMock(read=MagicMock(
                return_value=json.dumps({"violations": violations}).encode()
            ))
        }

    def test_blocks_too_few_annotations(self, before_event, after_event):
        plugin = self._setup_plugin(after_event)
        annotations = [
            {"label": "V1", "box": [0, 0, 0, 0], "severity": "high"},
        ]
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3_violations(3)
            event = before_event("draw_annotations", {"annotations": annotations})
            plugin.enforce_annotation_rules(event)

        assert event.cancel_tool is not None
        assert "mismatch" in event.cancel_tool.lower()

    def test_blocks_too_many_annotations(self, before_event, after_event):
        plugin = self._setup_plugin(after_event)
        annotations = [
            {"label": f"V{i}", "box": [0, 0, 0, 0], "severity": "high"}
            for i in range(5)
        ]
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3_violations(3)
            event = before_event("draw_annotations", {"annotations": annotations})
            plugin.enforce_annotation_rules(event)

        assert event.cancel_tool is not None
        assert "mismatch" in event.cancel_tool.lower()

    def test_allows_matching_count(self, before_event, after_event, sample_annotations):
        plugin = self._setup_plugin(after_event)
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3_violations(3)
            event = before_event("draw_annotations", {"annotations": sample_annotations})
            plugin.enforce_annotation_rules(event)

        assert event.cancel_tool is None


class TestAnnotationWorkflowPluginStructureValidation:
    """Tests for annotation structure enforcement."""

    def _setup_plugin_with_s3(self, after_event, violation_count):
        plugin = AnnotationWorkflowPlugin()
        plugin._compliance_json_bucket = "test-bucket"
        plugin._compliance_json_key = "report.json"
        plugin.track_tool_calls(after_event("load_s3_data", result="ok"))
        plugin.track_tool_calls(after_event("get_text_regions", result="ok"))
        return plugin

    def _mock_s3(self, count):
        violations = [{"title": f"V{i}"} for i in range(count)]
        return {
            "Body": MagicMock(read=MagicMock(
                return_value=json.dumps({"violations": violations}).encode()
            ))
        }

    def test_blocks_missing_label(self, before_event, after_event):
        plugin = self._setup_plugin_with_s3(after_event, 1)
        annotations = [{"box": [0, 0, 0, 0], "severity": "high"}]
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3(1)
            event = before_event("draw_annotations", {"annotations": annotations})
            plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "label" in event.cancel_tool.lower()

    def test_blocks_missing_box(self, before_event, after_event):
        plugin = self._setup_plugin_with_s3(after_event, 1)
        annotations = [{"label": "V0", "severity": "high"}]
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3(1)
            event = before_event("draw_annotations", {"annotations": annotations})
            plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "box" in event.cancel_tool.lower()

    def test_blocks_missing_severity(self, before_event, after_event):
        plugin = self._setup_plugin_with_s3(after_event, 1)
        annotations = [{"label": "V0", "box": [0, 0, 0, 0]}]
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3(1)
            event = before_event("draw_annotations", {"annotations": annotations})
            plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "severity" in event.cancel_tool.lower()

    def test_blocks_invalid_severity(self, before_event, after_event):
        plugin = self._setup_plugin_with_s3(after_event, 1)
        annotations = [{"label": "V0", "box": [0, 0, 0, 0], "severity": "critical"}]
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3(1)
            event = before_event("draw_annotations", {"annotations": annotations})
            plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "invalid severity" in event.cancel_tool.lower()

    def test_blocks_box_wrong_length(self, before_event, after_event):
        plugin = self._setup_plugin_with_s3(after_event, 1)
        annotations = [{"label": "V0", "box": [0, 0, 0], "severity": "high"}]
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3(1)
            event = before_event("draw_annotations", {"annotations": annotations})
            plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "box" in event.cancel_tool.lower()

    def test_blocks_box_not_list(self, before_event, after_event):
        plugin = self._setup_plugin_with_s3(after_event, 1)
        annotations = [{"label": "V0", "box": "0,0,0,0", "severity": "high"}]
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3(1)
            event = before_event("draw_annotations", {"annotations": annotations})
            plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "box" in event.cancel_tool.lower()

    def test_blocks_duplicate_labels(self, before_event, after_event):
        plugin = self._setup_plugin_with_s3(after_event, 2)
        annotations = [
            {"label": "Same Label", "box": [0, 0, 0, 0], "severity": "high"},
            {"label": "Same Label", "box": [10, 20, 30, 40], "severity": "medium"},
        ]
        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.return_value = self._mock_s3(2)
            event = before_event("draw_annotations", {"annotations": annotations})
            plugin.enforce_annotation_rules(event)
        assert event.cancel_tool is not None
        assert "duplicate" in event.cancel_tool.lower()


class TestAnnotationWorkflowPluginS3Failure:
    """Tests for S3 failure handling."""

    def test_blocks_when_s3_read_fails(self, before_event, after_event):
        plugin = AnnotationWorkflowPlugin()
        plugin._compliance_json_bucket = "test-bucket"
        plugin._compliance_json_key = "report.json"
        plugin.track_tool_calls(after_event("load_s3_data", result="ok"))
        plugin.track_tool_calls(after_event("get_text_regions", result="ok"))

        with patch("steering_hooks.boto3") as mock_boto3:
            mock_boto3.client.return_value.get_object.side_effect = Exception("Access Denied")
            event = before_event("draw_annotations", {
                "annotations": [{"label": "X", "box": [0, 0, 0, 0], "severity": "high"}]
            })
            plugin.enforce_annotation_rules(event)

        assert event.cancel_tool is not None
        assert "Could not read" in event.cancel_tool

    def test_blocks_when_no_bucket_captured(self, before_event, after_event):
        plugin = AnnotationWorkflowPlugin()
        plugin.track_tool_calls(after_event("load_s3_data", result="ok"))
        plugin.track_tool_calls(after_event("get_text_regions", result="ok"))

        event = before_event("draw_annotations", {
            "annotations": [{"label": "X", "box": [0, 0, 0, 0], "severity": "high"}]
        })
        plugin.enforce_annotation_rules(event)

        assert event.cancel_tool is not None

    def test_capture_s3_coords(self, before_event):
        plugin = AnnotationWorkflowPlugin()
        event = before_event("load_s3_data", {
            "image_bucket": "img-bucket",
            "image_key": "img.png",
            "json_bucket": "results-bucket",
            "json_key": "report.json",
        })
        plugin.capture_s3_coords(event)
        assert plugin._compliance_json_bucket == "results-bucket"
        assert plugin._compliance_json_key == "report.json"


# ============================================================
# ValidationWorkflowPlugin Tests
# ============================================================

class TestValidationWorkflowPluginOrdering:
    """Tests for validation tool ordering enforcement."""

    def test_blocks_analyze_without_load_compliance_report(self, before_event):
        plugin = ValidationWorkflowPlugin()
        event = before_event("analyze_annotated_image", {"bucket": "b", "key": "k"})
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is not None
        assert "load_compliance_report" in event.cancel_tool

    def test_blocks_store_without_load_compliance_report(self, before_event):
        plugin = ValidationWorkflowPlugin()
        event = before_event("store_validation_result", {
            "validation_status": "APPROVED", "issues": [],
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is not None
        assert "load_compliance_report" in event.cancel_tool

    def test_blocks_store_without_analyze(self, before_event, after_event):
        plugin = ValidationWorkflowPlugin()
        plugin.track_tool_calls(after_event("load_compliance_report", result="ok"))
        event = before_event("store_validation_result", {
            "validation_status": "APPROVED", "issues": [],
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is not None
        assert "analyze_annotated_image" in event.cancel_tool

    def test_allows_correct_ordering(self, before_event, after_event):
        plugin = ValidationWorkflowPlugin()
        plugin.track_tool_calls(after_event("load_compliance_report", result="ok"))
        plugin.track_tool_calls(after_event("analyze_annotated_image", result="ok"))
        event = before_event("store_validation_result", {
            "validation_status": "APPROVED",
            "issues": [],
            "feedback": "",
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is None


class TestValidationWorkflowPluginStatusValidation:
    """Tests for status/issues consistency enforcement."""

    def _make_ready_plugin(self, after_event):
        plugin = ValidationWorkflowPlugin()
        plugin.track_tool_calls(after_event("load_compliance_report", result="ok"))
        plugin.track_tool_calls(after_event("analyze_annotated_image", result="ok"))
        return plugin

    def test_blocks_invalid_status(self, before_event, after_event):
        plugin = self._make_ready_plugin(after_event)
        event = before_event("store_validation_result", {
            "validation_status": "PENDING",
            "issues": [],
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is not None
        assert "APPROVED" in event.cancel_tool
        assert "REJECTED" in event.cancel_tool

    def test_blocks_approved_with_issues(self, before_event, after_event):
        plugin = self._make_ready_plugin(after_event)
        event = before_event("store_validation_result", {
            "validation_status": "APPROVED",
            "issues": ["something is wrong"],
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is not None
        assert "APPROVED" in event.cancel_tool

    def test_blocks_rejected_without_issues(self, before_event, after_event):
        plugin = self._make_ready_plugin(after_event)
        event = before_event("store_validation_result", {
            "validation_status": "REJECTED",
            "issues": [],
            "feedback": "This is detailed feedback for agent 2",
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is not None
        assert "REJECTED" in event.cancel_tool

    def test_blocks_rejected_with_short_feedback(self, before_event, after_event):
        plugin = self._make_ready_plugin(after_event)
        event = before_event("store_validation_result", {
            "validation_status": "REJECTED",
            "issues": ["count mismatch"],
            "feedback": "bad",  # < 10 chars
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is not None
        assert "feedback" in event.cancel_tool.lower()

    def test_blocks_rejected_with_whitespace_only_feedback(self, before_event, after_event):
        plugin = self._make_ready_plugin(after_event)
        event = before_event("store_validation_result", {
            "validation_status": "REJECTED",
            "issues": ["something"],
            "feedback": "         ",  # whitespace only, strip() < 10
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is not None

    def test_allows_approved_empty_issues(self, before_event, after_event):
        plugin = self._make_ready_plugin(after_event)
        event = before_event("store_validation_result", {
            "validation_status": "APPROVED",
            "issues": [],
            "feedback": "",
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is None

    def test_allows_rejected_with_issues_and_feedback(self, before_event, after_event):
        plugin = self._make_ready_plugin(after_event)
        event = before_event("store_validation_result", {
            "validation_status": "REJECTED",
            "issues": ["Missing annotation for violation #2", "Extra annotation found"],
            "feedback": "You need to add an annotation for the 'Missing Drug Facts' violation and remove the extra box on the bottom-right.",
        })
        plugin.enforce_validation_rules(event)
        assert event.cancel_tool is None
