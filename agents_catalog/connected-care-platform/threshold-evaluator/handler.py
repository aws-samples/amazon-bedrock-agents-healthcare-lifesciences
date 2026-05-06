"""
Threshold Evaluator — Checks patient vitals and device telemetry against trigger rules.
Fires EventBridge events and writes alerts to DynamoDB when thresholds are breached.
Runs on a 1-minute CloudWatch Events schedule.
"""

import json
import os
import uuid
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
eventbridge = boto3.client("events", region_name=os.environ.get("AWS_REGION", "us-east-1"))

patients_table = dynamodb.Table(os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients"))
vitals_table = dynamodb.Table(os.environ.get("DYNAMODB_VITALS_TABLE", "connected-care-vitals"))
telemetry_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry"))
devices_table = dynamodb.Table(os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices"))
inventory_table = dynamodb.Table(os.environ.get("DYNAMODB_INVENTORY_TABLE", "connected-care-inventory"))
alerts_table = dynamodb.Table(os.environ.get("DYNAMODB_ALERTS_TABLE", "connected-care-proactive-alerts"))

EVENT_BUS = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")
COOLDOWN_MINUTES = 30


def _check_cooldown(rule_id: str, entity_id: str) -> bool:
    """Return True if this rule+entity is in cooldown (should NOT fire)."""
    try:
        resp = alerts_table.query(
            KeyConditionExpression=Key("alert_type").eq(f"{rule_id}#{entity_id}"),
            ScanIndexForward=False, Limit=1,
        )
        if resp.get("Items"):
            last = resp["Items"][0]
            last_ts = datetime.fromisoformat(last["timestamp"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last_ts < timedelta(minutes=COOLDOWN_MINUTES):
                return True
    except Exception:
        pass
    return False


def _write_alert(rule_id: str, entity_id: str, alert: dict):
    """Write an alert to the proactive alerts table."""
    now = datetime.now(timezone.utc).isoformat()
    alerts_table.put_item(Item={
        "alert_type": f"{rule_id}#{entity_id}",
        "timestamp": now,
        "alert_id": str(uuid.uuid4()),
        "rule_id": rule_id,
        "entity_id": entity_id,
        "severity": alert.get("severity", "HIGH"),
        "title": alert.get("title", ""),
        "patient_id": alert.get("patient_id", ""),
        "patient_name": alert.get("patient_name", ""),
        "room": alert.get("room", ""),
        "workflow_id": alert.get("workflow_id", ""),
        "reasoning": alert.get("reasoning", []),
        "recommended_action": alert.get("recommended_action", ""),
        "acknowledged": False,
        "ttl": int(time.time()) + 86400,  # 24h TTL
    })


def _get_latest_vitals(patient_id: str) -> dict:
    """Get the most recent vitals for a patient."""
    try:
        resp = vitals_table.query(
            KeyConditionExpression=Key("patient_id").eq(patient_id),
            ScanIndexForward=False, Limit=1,
        )
        if resp.get("Items"):
            return resp["Items"][0]
    except Exception:
        pass
    return {}


def _get_latest_bed_telemetry(device_id: str) -> dict:
    """Get the most recent smart bed telemetry."""
    try:
        resp = telemetry_table.query(
            KeyConditionExpression=Key("device_id").eq(device_id),
            ScanIndexForward=False, Limit=1,
        )
        if resp.get("Items"):
            return resp["Items"][0].get("telemetry", {})
    except Exception:
        pass
    return {}


def evaluate_deterioration(patient: dict) -> dict | None:
    """WF-03: Check for patient deterioration using Early Warning Score."""
    pid = patient["patient_id"]
    if _check_cooldown("deterioration", pid):
        return None

    vitals = _get_latest_vitals(pid)
    if not vitals:
        return None

    # Simple EWS calculation
    score = 0
    reasons = []

    hr = float(vitals.get("heart_rate", 75))
    if hr > 110 or hr < 50:
        score += 3
        reasons.append({"factor": f"Heart rate {hr:.0f} bpm (abnormal)", "source": "Vitals", "weight": "high"})
    elif hr > 100 or hr < 55:
        score += 1
        reasons.append({"factor": f"Heart rate {hr:.0f} bpm (borderline)", "source": "Vitals", "weight": "medium"})

    sbp = float(vitals.get("blood_pressure_systolic", 120))
    if sbp < 85 or sbp > 170:
        score += 3
        reasons.append({"factor": f"Systolic BP {sbp:.0f} mmHg (critical)", "source": "Vitals", "weight": "high"})
    elif sbp < 95 or sbp > 150:
        score += 1
        reasons.append({"factor": f"Systolic BP {sbp:.0f} mmHg (borderline)", "source": "Vitals", "weight": "medium"})

    spo2 = float(vitals.get("spo2", 98))
    if spo2 < 90:
        score += 3
        reasons.append({"factor": f"SpO2 {spo2:.0f}% (critical)", "source": "Vitals", "weight": "high"})
    elif spo2 < 94:
        score += 1
        reasons.append({"factor": f"SpO2 {spo2:.0f}% (low)", "source": "Vitals", "weight": "medium"})

    rr = float(vitals.get("respiratory_rate", 16))
    if rr > 28 or rr < 9:
        score += 3
        reasons.append({"factor": f"Respiratory rate {rr:.0f}/min (abnormal)", "source": "Vitals", "weight": "high"})
    elif rr > 22 or rr < 11:
        score += 1
        reasons.append({"factor": f"Respiratory rate {rr:.0f}/min (borderline)", "source": "Vitals", "weight": "medium"})

    temp = float(vitals.get("temperature", 98.6))
    if temp > 102 or temp < 95.5:
        score += 3
        reasons.append({"factor": f"Temperature {temp:.1f}°F (critical)", "source": "Vitals", "weight": "high"})
    elif temp > 100.5 or temp < 96.5:
        score += 1
        reasons.append({"factor": f"Temperature {temp:.1f}°F (borderline)", "source": "Vitals", "weight": "medium"})

    if score >= 5:
        severity = "CRITICAL" if score >= 8 else "HIGH"
        return {
            "rule_id": "deterioration",
            "workflow_id": "WF-03",
            "patient_id": pid,
            "patient_name": patient.get("name", "Unknown"),
            "room": patient.get("room", "Unknown"),
            "severity": severity,
            "title": f"Patient Deterioration — EWS {score}",
            "reasoning": reasons,
            "recommended_action": f"Immediate clinical review. Early Warning Score {score} indicates deterioration risk.",
        }
    return None


def evaluate_pressure_injury(patient: dict, bed_device_id: str) -> dict | None:
    """WF-10: Check for pressure injury risk."""
    pid = patient["patient_id"]
    if _check_cooldown("pressure_injury", pid):
        return None

    braden = patient.get("braden_score", {})
    braden_total = int(braden.get("total", 23))
    print(f"  pressure_injury {pid}: raw_braden={braden}, braden_total={braden_total}")
    if braden_total > 14:
        return None  # Low risk, skip

    bed_tel = _get_latest_bed_telemetry(bed_device_id)
    if not bed_tel:
        print(f"  pressure_injury {pid}: no bed telemetry for {bed_device_id}")
        return None

    hours_since = float(bed_tel.get("hours_since_reposition", 0))
    pressure_zones = bed_tel.get("pressure_zones", {})
    sacral = pressure_zones.get("sacrum", {})
    sacral_pressure = float(sacral.get("pressure_mmhg", 0))

    print(f"  pressure_injury {pid}: braden={braden_total}, hours={hours_since}, sacral={sacral_pressure}")

    if braden_total <= 12 and hours_since > 2 and sacral_pressure > 40:
        reasons = [
            {"factor": f"Braden score {braden_total} ({braden.get('risk_level', 'HIGH')} risk)", "source": "Patient profile", "weight": "high"},
            {"factor": f"{hours_since:.1f} hours since last repositioning (exceeds 2h)", "source": f"Smart Bed {bed_device_id}", "weight": "high"},
            {"factor": f"Sacral pressure {sacral_pressure:.0f} mmHg (threshold: 40 mmHg)", "source": f"Smart Bed {bed_device_id} pressure map", "weight": "high"},
        ]
        return {
            "rule_id": "pressure_injury",
            "workflow_id": "WF-10",
            "patient_id": pid,
            "patient_name": patient.get("name", "Unknown"),
            "room": patient.get("room", "Unknown"),
            "severity": "HIGH",
            "title": "Pressure Injury Risk — Repositioning Overdue",
            "reasoning": reasons,
            "recommended_action": "Reposition patient immediately. Assess sacral skin integrity. Float heels.",
        }
    return None


def evaluate_fall_risk(patient: dict, bed_device_id: str) -> dict | None:
    """WF-01/WF-09: Check for fall risk from bed exit + medications."""
    pid = patient["patient_id"]
    if _check_cooldown("fall_risk", pid):
        print(f"  fall_risk {pid}: in cooldown, skipping")
        return None

    fall_risk = patient.get("fall_risk", {})
    if fall_risk.get("level") not in ("HIGH", "MODERATE"):
        print(f"  fall_risk {pid}: risk level {fall_risk.get('level')} not HIGH/MODERATE, skipping")
        return None

    bed_tel = _get_latest_bed_telemetry(bed_device_id)
    if not bed_tel:
        print(f"  fall_risk {pid}: no bed telemetry for {bed_device_id}")
        return None

    restlessness = float(bed_tel.get("restlessness_score", 0))
    print(f"  fall_risk {pid}: restlessness={restlessness}")
    if restlessness < 6:
        print(f"  fall_risk {pid}: restlessness {restlessness} < 6, skipping")
        return None

    # Check for orthostatic-risk medications
    meds = patient.get("medications", [])
    risky_meds = [m for m in meds if any(drug in m.get("name", "").lower() for drug in ["furosemide", "lisinopril", "metoprolol", "amlodipine", "oxycodone"])]

    if risky_meds:
        reasons = [
            {"factor": f"Restlessness score {restlessness:.1f} (elevated)", "source": f"Smart Bed {bed_device_id}", "weight": "high"},
            {"factor": f"Fall risk level: {fall_risk.get('level')}", "source": "Patient profile", "weight": "high"},
            {"factor": f"Orthostatic-risk medications: {', '.join(m['name'] for m in risky_meds)}", "source": "Medication list", "weight": "medium"},
        ]
        factors = fall_risk.get("factors", [])
        if factors:
            reasons.append({"factor": f"Risk factors: {', '.join(f.replace('_', ' ') for f in factors[:3])}", "source": "Fall risk assessment", "weight": "medium"})

        return {
            "rule_id": "fall_risk",
            "workflow_id": "WF-01",
            "patient_id": pid,
            "patient_name": patient.get("name", "Unknown"),
            "room": patient.get("room", "Unknown"),
            "severity": "HIGH",
            "title": "Fall Risk — Elevated Restlessness + High-Risk Medications",
            "reasoning": reasons,
            "recommended_action": "Immediate bedside check. Verify bed rails up and alarm armed. Assist with ambulation if needed.",
        }
    return None


def evaluate_stockout(item: dict) -> dict | None:
    """WF-06: Check for critical supply stockout."""
    item_id = item.get("item_id", "")
    if _check_cooldown("stockout", item_id):
        return None

    stock = float(item.get("current_stock", 999))
    burn_rate = float(item.get("burn_rate_per_hour", 0))
    if burn_rate <= 0:
        return None

    hours_left = stock / burn_rate
    if hours_left > 4:
        return None

    dependent = item.get("dependent_patients", [])
    reasons = [
        {"factor": f"Current stock: {int(stock)} {item.get('unit', 'units')}", "source": "Inventory", "weight": "high"},
        {"factor": f"Burn rate: {burn_rate:.1f}/hr — depletes in {hours_left:.1f} hours", "source": "Inventory", "weight": "high"},
    ]
    if dependent:
        reasons.append({"factor": f"Patients affected: {', '.join(dependent)}", "source": "Patient assignments", "weight": "high"})
    subs = item.get("substitute_items", [])
    if not subs:
        reasons.append({"factor": "No substitute items available", "source": "Inventory", "weight": "high"})

    return {
        "rule_id": "stockout",
        "workflow_id": "WF-06",
        "patient_id": dependent[0] if dependent else "",
        "patient_name": "",
        "room": item.get("floor", ""),
        "severity": "CRITICAL" if hours_left <= 2 else "HIGH",
        "title": f"Critical Stockout — {item.get('item_name', item_id)}",
        "reasoning": reasons,
        "recommended_action": f"Immediate reorder for {item.get('item_name')}. Check substitutes on other floors.",
    }


def evaluate_device_failure(device: dict) -> dict | None:
    """WF-04: Check for imminent device failure."""
    did = device.get("device_id", "")
    if _check_cooldown("device_failure", did):
        return None
    if device.get("status") != "active":
        return None

    tel = _get_latest_bed_telemetry(did)  # Works for any device, not just beds
    if not tel:
        return None

    errors = int(tel.get("error_count", 0))
    drift = float(tel.get("calibration_drift", 0))
    battery = float(tel.get("battery_level", 100))

    reasons = []
    severity_score = 0

    if errors > 50:
        reasons.append({"factor": f"Error count: {errors} (critical threshold: 50)", "source": "Device telemetry", "weight": "high"})
        severity_score += 3
    if drift > 5.0:
        reasons.append({"factor": f"Calibration drift: {drift:.1f}% (critical threshold: 5.0%)", "source": "Device telemetry", "weight": "high"})
        severity_score += 3
    if battery < 10:
        reasons.append({"factor": f"Battery: {battery:.0f}% (critical threshold: 10%)", "source": "Device telemetry", "weight": "high"})
        severity_score += 2

    if severity_score >= 3:
        return {
            "rule_id": "device_failure",
            "workflow_id": "WF-04",
            "patient_id": device.get("assigned_patient_id", ""),
            "patient_name": "",
            "room": device.get("location", ""),
            "severity": "CRITICAL" if severity_score >= 5 else "HIGH",
            "title": f"Device Failure Risk — {did} ({device.get('model', '')})",
            "reasoning": reasons,
            "recommended_action": f"Assess device {did} immediately. Locate replacement. Check patient monitoring continuity.",
        }
    return None


# Smart bed to patient mapping (from seed data)
BED_PATIENT_MAP = {
    "D-7001": "P-10001",
    "D-7002": "P-10002",
    "D-7003": "P-10003",
    "D-7004": "P-10004",
    "D-7005": "P-10005",
}


def handler(event, context):
    """Evaluate all trigger rules against current data."""
    alerts_fired = 0
    print("Threshold evaluator starting...")

    # Load all patients
    patients_resp = patients_table.scan()
    patients = {p["patient_id"]: p for p in patients_resp.get("Items", [])}
    print(f"Loaded {len(patients)} patients")

    # --- Patient-based rules ---
    for pid, patient in patients.items():
        # WF-03: Deterioration
        try:
            alert = evaluate_deterioration(patient)
            if alert:
                _write_alert(alert["rule_id"], pid, alert)
                alerts_fired += 1
                print(f"ALERT: deterioration for {pid}")
        except Exception as e:
            print(f"ERROR deterioration {pid}: {e}")

        # Find this patient's smart bed
        bed_id = None
        for bid, bpid in BED_PATIENT_MAP.items():
            if bpid == pid:
                bed_id = bid
                break

        if bed_id:
            # WF-10: Pressure injury
            try:
                alert = evaluate_pressure_injury(patient, bed_id)
                if alert:
                    _write_alert(alert["rule_id"], pid, alert)
                    alerts_fired += 1
                    print(f"ALERT: pressure_injury for {pid}")
                else:
                    print(f"No pressure_injury alert for {pid} (bed {bed_id})")
            except Exception as e:
                print(f"ERROR pressure_injury {pid}: {e}")

            # WF-01: Fall risk
            try:
                alert = evaluate_fall_risk(patient, bed_id)
                if alert:
                    _write_alert(alert["rule_id"], pid, alert)
                    alerts_fired += 1
                    print(f"ALERT: fall_risk for {pid}")
            except Exception as e:
                print(f"ERROR fall_risk {pid}: {e}")

    # --- Inventory rules ---
    try:
        inv_resp = inventory_table.scan()
        for item in inv_resp.get("Items", []):
            try:
                alert = evaluate_stockout(item)
                if alert:
                    _write_alert(alert["rule_id"], item["item_id"], alert)
                    alerts_fired += 1
                    print(f"ALERT: stockout for {item['item_id']}")
            except Exception as e:
                print(f"ERROR stockout {item.get('item_id')}: {e}")
    except Exception as e:
        print(f"ERROR inventory scan: {e}")

    # --- Device rules ---
    try:
        dev_resp = devices_table.scan()
        for device in dev_resp.get("Items", []):
            try:
                alert = evaluate_device_failure(device)
                if alert:
                    _write_alert(alert["rule_id"], device["device_id"], alert)
                    alerts_fired += 1
                    print(f"ALERT: device_failure for {device['device_id']}")
            except Exception as e:
                print(f"ERROR device_failure {device.get('device_id')}: {e}")
    except Exception as e:
        print(f"ERROR device scan: {e}")

    print(f"Evaluation complete. Alerts fired: {alerts_fired}")
    return {
        "statusCode": 200,
        "body": json.dumps({"alerts_fired": alerts_fired, "timestamp": datetime.now(timezone.utc).isoformat()}),
    }
