"""
Steering hooks:
plugins that enforce behavioral rules deterministically via Strands hooks,
catching errors before tools execute rather than after the fact.
"""

import json
import logging
import boto3
from strands.plugins import Plugin, hook
from strands.hooks import BeforeToolCallEvent, AfterToolCallEvent

logger = logging.getLogger(__name__)

## --- Agent 1: Compliance Analysis Steering --- ##
class ComplianceWorkflowPlugin(Plugin):
    """Enforces tool call ordering and violation structure for Agent 1."""

    name = "compliance-workflow-steering"

    def __init__(self):
        super().__init__()
        self._tool_history = []

    @hook
    def track_tool_calls(self, event: AfterToolCallEvent) -> None:
        """Track successful tool calls for workflow ordering validation."""
        if not isinstance(event.result, Exception):
            self._tool_history.append(event.tool_use.get("name", ""))

    @hook
    def enforce_workflow_and_structure(self, event: BeforeToolCallEvent) -> None:
        """Enforce tool ordering and validate violation data structure."""
        tool_name = event.tool_use.get("name", "")

        # workflow ordering: must consult the KB before storing a report
        if tool_name == "store_compliance_report":
            if "retrieve" not in self._tool_history:
                event.cancel_tool = (
                    "STEERING: You must call retrieve to check regulatory requirements before storing the compliance report."
                )
                logger.info("BLOCKED 'store_compliance_report' tool (no KB retrieval yet)")
                return

            # Violation structure validation
            violations_str = event.tool_use.get("input", {}).get("violations", "")
            try:
                violations = json.loads(violations_str) if isinstance(violations_str, str) else violations_str
                if not isinstance(violations, list):
                    event.cancel_tool = (
                        "STEERING: violations must be a JSON array. Got a non-array type."
                    )
                    return

                required_fields = {"title", "description", "severity"}
                valid_severities = {"high", "medium", "low"}

                for i, v in enumerate(violations):
                    missing = required_fields - set(v.keys())
                    if missing:
                        event.cancel_tool = (
                            f"STEERING: Violation at index {i} is missing required fields: {missing}. "
                            f"Each violation must have: title, description, severity."
                        )
                        logger.info(f"Storing rejected: violation {i} missing {missing}")
                        return

                    if v.get("severity") not in valid_severities:
                        event.cancel_tool = (
                            f"STEERING: Violation at index {i} has invalid severity '{v.get('severity')}'. "
                            f"Must be one of: high, medium, low."
                        )
                        logger.info(f"Storing rejected: invalid severity at index {i}")
                        return

            except (json.JSONDecodeError, TypeError):
                event.cancel_tool = (
                    "STEERING: violations must be a valid JSON array string. "
                    "Example: '[{\"title\":\"...\",\"description\":\"...\",\"severity\":\"high\"}]'"
                )
                logger.info("Storing rejected: invalid JSON in violations")
                return

        logger.debug(f"Allowing {tool_name} ✅")


## --- Agent 2: Annotation Steering --- ##
class AnnotationWorkflowPlugin(Plugin):
    """Enforces annotation rules for Agent 2."""

    name = "annotation-workflow-steering"

    def __init__(self):
        super().__init__()
        self._tool_history = []
        self._compliance_json_bucket = None
        self._compliance_json_key = None

    @hook
    def capture_s3_coords(self, event: BeforeToolCallEvent) -> None:
        """Capture the S3 bucket/key from load_s3_data input params."""
        tool_name = event.tool_use.get("name", "")
        if tool_name == "load_s3_data":
            inputs = event.tool_use.get("input", {})
            self._compliance_json_bucket = inputs.get("json_bucket")
            self._compliance_json_key = inputs.get("json_key")
            logger.info(
                f"Steering: captured compliance report location: "
                f"s3://{self._compliance_json_bucket}/{self._compliance_json_key}"
            )

    @hook
    def track_tool_calls(self, event: AfterToolCallEvent) -> None:
        """Track successful tool calls for workflow ordering."""
        if not isinstance(event.result, Exception):
            self._tool_history.append(event.tool_use.get("name", ""))

    def _get_violations_from_s3(self):
        """Read violations directly from S3 — no ToolResult parsing needed."""
        if not self._compliance_json_bucket or not self._compliance_json_key:
            return None, None
        try:
            s3 = boto3.client('s3')
            response = s3.get_object(
                Bucket=self._compliance_json_bucket,
                Key=self._compliance_json_key
            )
            data = json.loads(response['Body'].read().decode('utf-8'))
            violations = data.get("violations", [])
            titles = [v.get("title", "") for v in violations]
            return len(violations), titles
        except Exception as e:
            logger.warning(f"Steering: could not read violations from S3: {e}")
            return None, None

    @hook
    def enforce_annotation_rules(self, event: BeforeToolCallEvent) -> None:
        """Enforce workflow ordering and annotation correctness."""
        tool_name = event.tool_use.get("name", "")

        # --- Workflow ordering ---
        if tool_name == "get_text_regions" and "load_s3_data" not in self._tool_history:
            event.cancel_tool = (
                "STEERING: You must call load_s3_data first to get the compliance violations before requesting text regions."
            )
            logger.info("BLOCKED 'get_text_regions' tool ('load_s3_data' not called)")
            return

        if tool_name == "draw_annotations":
            if "load_s3_data" not in self._tool_history:
                event.cancel_tool = (
                    "STEERING: You must call load_s3_data first to get the compliance violations before drawing annotations."
                )
                logger.info("BLOCKED 'draw_annotations' tool ('load_s3_data' not called)")
                return

            if "get_text_regions" not in self._tool_history:
                event.cancel_tool = (
                    "STEERING: You must call get_text_regions first to get text coordinates before drawing annotations."
                )
                logger.info("BLOCKED 'draw_annotations' tool ('get_text_regions' not called)")
                return

            # Read violation count directly from S3
            violation_count, violation_titles = self._get_violations_from_s3()

            if violation_count is None:
                event.cancel_tool = (
                    "STEERING: Could not read violation count from the compliance report in S3. Ensure load_s3_data was called with valid json_bucket and json_key parameters."
                )
                logger.info("BLOCKED 'draw_annotations' tool (could not read S3 report)")
                return

            annotations = event.tool_use.get("input", {}).get("annotations", [])

            # Count check 
            if len(annotations) != violation_count:
                event.cancel_tool = (
                    f"STEERING: Annotation count mismatch. You provided {len(annotations)} annotations, but there are {violation_count} violations. These must be exactly equal!"
                    f"Expected violations: {violation_titles}"
                )
                logger.info(
                    f"BLOCKED 'draw_annotations' tool (count mismatch)"
                    f"({len(annotations)} vs {violation_count})"
                )
                return

            # Structure validation
            valid_severities = {"high", "medium", "low"}
            seen_labels = set()

            for i, ann in enumerate(annotations):
                # Required fields
                if "label" not in ann:
                    event.cancel_tool = (
                        f"STEERING: Annotation at index {i} is missing 'label' field."
                    )
                    return
                if "box" not in ann:
                    event.cancel_tool = (
                        f"STEERING: Annotation at index {i} is missing 'box' field. "
                        f"Use [0, 0, 0, 0] for sidebar items."
                    )
                    return
                if "severity" not in ann:
                    event.cancel_tool = (
                        f"STEERING: Annotation at index {i} is missing 'severity' field."
                    )
                    return

                # Severity validation
                if ann["severity"] not in valid_severities:
                    event.cancel_tool = (
                        f"STEERING: Annotation at index {i} has invalid severity '{ann['severity']}'. "
                        f"Must be one of: high, medium, low."
                    )
                    return

                # Box format validation
                box = ann.get("box", [])
                if not isinstance(box, list) or len(box) != 4:
                    event.cancel_tool = (
                        f"STEERING: Annotation at index {i} has invalid box format. "
                        f"Must be [x1, y1, x2, y2] with 4 integer values."
                    )
                    return

                # Duplicate check
                label = ann["label"]
                if label in seen_labels:
                    event.cancel_tool = (
                        f"STEERING: Duplicate annotation label '{label}' at index {i}. "
                        f"Each violation must have exactly one annotation."
                    )
                    return
                seen_labels.add(label)

        logger.debug(f"Allowing {tool_name} ✅")


## --- Agent 3: Validation Steering --- ##

class ValidationWorkflowPlugin(Plugin):
    """Enforces validation rules for Agent 3."""

    name = "validation-workflow-steering"

    def __init__(self):
        super().__init__()
        self._tool_history = []

    @hook
    def track_tool_calls(self, event: AfterToolCallEvent) -> None:
        """Track successful tool calls."""
        if not isinstance(event.result, Exception):
            self._tool_history.append(event.tool_use.get("name", ""))

    @hook
    def enforce_validation_rules(self, event: BeforeToolCallEvent) -> None:
        """Enforce workflow ordering and result consistency."""
        tool_name = event.tool_use.get("name", "")

        # Workflow ordering
        if tool_name == "analyze_annotated_image" and "load_compliance_report" not in self._tool_history:
            event.cancel_tool = (
                "STEERING: You must call load_compliance_report first to get the violations list before analyzing the annotated image."
            )
            logger.info("BLOCKED 'analyze_annotated_image' tool (no compliance report loaded)")
            return

        if tool_name == "store_validation_result":
            if "load_compliance_report" not in self._tool_history:
                event.cancel_tool = (
                    "STEERING: You must call load_compliance_report before storing validation results."
                )
                logger.info("BLOCKED 'store_validation_result' tool (no report loaded)")
                return

            if "analyze_annotated_image" not in self._tool_history:
                event.cancel_tool = (
                    "STEERING: You must call analyze_annotated_image before storing validation results."
                )
                logger.info("BLOCKED 'store_validation_result' tool (no image analysis found)")
                return

            # Status/issues consistency 
            inputs = event.tool_use.get("input", {})
            status = inputs.get("validation_status", "")
            issues = inputs.get("issues", [])

            if status not in ("APPROVED", "REJECTED"):
                event.cancel_tool = (
                    f"STEERING: Invalid validation_status '{status}'. "
                    f"Must be either 'APPROVED' or 'REJECTED'."
                )
                logger.info(f"Storing rejected: invalid status '{status}'")
                return

            if status == "APPROVED" and len(issues) > 0:
                event.cancel_tool = (
                    "STEERING: Cannot set status to APPROVED with non-empty issues list. "
                    "Either clear the issues list or set status to REJECTED."
                )
                logger.info("Storing rejected: status is 'APPROVED', but there are still issues")
                return

            if status == "REJECTED" and len(issues) == 0:
                event.cancel_tool = (
                    "STEERING: Cannot set status to REJECTED with an empty issues list. "
                    "You must specify at least one issue when rejecting."
                )
                logger.info("Storing rejected: status is 'REJECTED', but no issues found")
                return

            # Feedback required on rejection 
            feedback = inputs.get("feedback", "")
            if status == "REJECTED" and (not feedback or len(feedback.strip()) < 10):
                event.cancel_tool = (
                    "STEERING: REJECTED status requires meaningful feedback for Agent 2. "
                    "Provide detailed feedback listing missing violations and what to fix."
                )
                logger.info("Storing rejected: no meaningful feedback for Agent 2")
                return

        logger.debug(f"Allowing {tool_name} ✅")
