"""Tool: Analyze vital sign trends for a patient."""

import os
from datetime import datetime, timedelta, timezone

import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .phi_access import check_phi_access, phi_access_denied_response

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
vitals_table = dynamodb.Table(os.environ.get("DYNAMODB_VITALS_TABLE", "connected-care-vitals"))
patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))


@tool
def analyze_vital_trends(patient_id: str, hours: int = 4) -> dict:
    """Retrieve vital sign trend data with statistical summary for the agent
    to reason about deterioration risk.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        hours: Number of hours of history to analyze (default: 4, max: 24)

    Returns:
        Per-vital-sign statistics including min, max, average, latest value,
        trend direction, and the patient's alert thresholds for comparison.
    """
    if not check_phi_access(patient_id):
        return phi_access_denied_response(patient_id)

    hours = min(hours, 24)
    start_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # Get vitals history
    vitals_response = vitals_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id) & Key("timestamp").gte(start_time),
        ScanIndexForward=True,
    )
    items = vitals_response.get("Items", [])

    if not items:
        return {"patient_id": patient_id, "error": f"No data in the last {hours} hours"}

    # Get patient thresholds
    patient_response = patients_table.get_item(Key={"patient_id": patient_id})
    patient = patient_response.get("Item", {})
    thresholds = patient.get("alert_thresholds", {})

    vital_names = [
        "heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic",
        "temperature", "spo2", "respiratory_rate", "blood_glucose",
    ]

    analysis = {}
    for vital in vital_names:
        values = [float(item["vitals"].get(vital, 0)) for item in items if vital in item.get("vitals", {})]
        if not values:
            continue

        # Calculate trend (simple linear: compare first half avg to second half avg)
        mid = len(values) // 2
        if mid > 0:
            first_half_avg = sum(values[:mid]) / mid
            second_half_avg = sum(values[mid:]) / (len(values) - mid)
            diff = second_half_avg - first_half_avg
            if abs(diff) < 1:
                trend = "stable"
            elif diff > 0:
                trend = "rising"
            else:
                trend = "falling"
        else:
            trend = "insufficient_data"

        threshold = thresholds.get(vital, {})
        latest = values[-1]
        threshold_low = float(threshold.get("low", 0))
        threshold_high = float(threshold.get("high", 999))

        # Check if latest value is outside thresholds
        if latest < threshold_low:
            threshold_status = "BELOW_THRESHOLD"
        elif latest > threshold_high:
            threshold_status = "ABOVE_THRESHOLD"
        else:
            threshold_status = "WITHIN_NORMAL"

        analysis[vital] = {
            "latest_value": latest,
            "min": min(values),
            "max": max(values),
            "average": round(sum(values) / len(values), 1),
            "readings_count": len(values),
            "trend": trend,
            "threshold_low": threshold_low,
            "threshold_high": threshold_high,
            "threshold_status": threshold_status,
        }

    return {
        "patient_id": patient_id,
        "patient_name": patient.get("name", "Unknown"),
        "risk_profile": patient.get("risk_profile", "unknown"),
        "analysis_window_hours": hours,
        "total_readings": len(items),
        "vital_analysis": analysis,
    }
