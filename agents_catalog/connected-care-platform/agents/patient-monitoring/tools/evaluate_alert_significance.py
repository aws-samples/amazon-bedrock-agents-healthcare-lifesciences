"""Tool: Evaluate whether an alert should be suppressed, bundled, or escalated."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta, timezone

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
alert_history_table = dynamodb.Table(os.environ.get("ALERT_HISTORY_TABLE", "connected-care-alert-history"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))


@tool
def evaluate_alert_significance(
    patient_id: str,
    alert_type: str,
    severity: str,
    detail: str,
) -> dict:
    """Evaluate whether a clinical alert should be suppressed, bundled, or escalated.

    Uses alert history, device reliability, and patient baseline to triage alerts
    and reduce nurse alert fatigue. CRITICAL alerts are NEVER suppressed.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        alert_type: Type of alert (vital_threshold, device_alarm, repositioning, fall_risk, medication)
        severity: Alert severity (CRITICAL, HIGH, MEDIUM, LOW)
        detail: Description of the alert condition

    Returns:
        Triage result (ESCALATE, BUNDLE, or SUPPRESS) with reasoning.
    """
    # CRITICAL alerts are NEVER suppressed
    if severity == "CRITICAL":
        return {
            "triage_result": "ESCALATE",
            "reason": "CRITICAL severity -- always escalated immediately",
            "suppress": False,
            "patient_id": patient_id,
            "alert_type": alert_type,
            "severity": severity,
        }

    # Check for repeat alerts in the last 30 minutes
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    recent_alerts = []
    try:
        # Scan for recent alerts for this patient and type
        response = alert_history_table.scan(
            FilterExpression="patient_id = :pid AND alert_type = :atype AND #ts >= :cutoff",
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues={
                ":pid": patient_id,
                ":atype": alert_type,
                ":cutoff": cutoff,
            },
            Limit=20,
        )
        recent_alerts = response.get("Items", [])
    except Exception:
        pass

    repeat_count = len(recent_alerts)

    # Check device reliability if this is a device alarm
    device_unreliable = False
    if alert_type == "device_alarm" and "D-" in detail:
        # Extract device ID from detail
        import re
        device_match = re.search(r'D-\d+', detail)
        if device_match:
            device_id = device_match.group()
            try:
                device_resp = devices_table.get_item(Key={"device_id": device_id})
                device = device_resp.get("Item", {})
                if device.get("risk_profile") in ("critical", "moderate"):
                    device_unreliable = True
            except Exception:
                pass

    # Check patient baseline
    patient_baseline_normal = False
    try:
        patient_resp = patients_table.get_item(Key={"patient_id": patient_id})
        patient = patient_resp.get("Item", {})
        risk_profile = patient.get("risk_profile", "")
        # If patient is stable/low-risk and alert is LOW/MEDIUM, likely baseline
        if risk_profile in ("stable", "low") and severity in ("LOW", "MEDIUM"):
            patient_baseline_normal = True
    except Exception:
        pass

    # Triage decision
    reasons = []

    # Suppress: repeat alerts
    if repeat_count >= 3 and severity != "HIGH":
        reasons.append(f"Repeat alert: {repeat_count} similar alerts in last 30 minutes")

    # Suppress: device noise
    if device_unreliable and severity == "LOW":
        reasons.append("Device has known reliability issues")

    # Suppress: patient baseline
    if patient_baseline_normal:
        reasons.append("Value is within expected range for this patient's baseline")

    # Decision
    if reasons and severity in ("LOW", "MEDIUM"):
        return {
            "triage_result": "SUPPRESS",
            "reason": ". ".join(reasons),
            "suppress": True,
            "patient_id": patient_id,
            "alert_type": alert_type,
            "severity": severity,
            "repeat_count": repeat_count,
            "device_unreliable": device_unreliable,
        }

    if severity == "MEDIUM" and repeat_count >= 1:
        return {
            "triage_result": "BUNDLE",
            "reason": f"Medium severity with {repeat_count} recent similar alerts. Bundle for summary delivery.",
            "suppress": False,
            "patient_id": patient_id,
            "alert_type": alert_type,
            "severity": severity,
        }

    # Default: escalate
    return {
        "triage_result": "ESCALATE",
        "reason": "Alert meets escalation criteria",
        "suppress": False,
        "patient_id": patient_id,
        "alert_type": alert_type,
        "severity": severity,
    }
