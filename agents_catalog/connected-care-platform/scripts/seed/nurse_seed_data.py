"""Seed data for nurse assignments and alert history for the Alert Fatigue Management system."""

import uuid
from datetime import datetime, timedelta, timezone

NOW = datetime.now(timezone.utc)
SHIFT_ID = f"SHIFT-{NOW.strftime('%Y-%m-%d')}-NIGHT"

NURSE_ASSIGNMENTS = [
    {
        "nurse_id": "NRS-001",
        "shift_id": SHIFT_ID,
        "name": "RN Maria Santos",
        "role": "Primary Nurse",
        "assigned_patients": ["P-10001", "P-10002"],
        "assigned_rooms": ["ICU-412", "Floor3-308"],
        "shift_start": (NOW.replace(hour=22, minute=0, second=0) - timedelta(days=1)).isoformat(),
        "shift_end": NOW.replace(hour=6, minute=0, second=0).isoformat(),
        "status": "active",
    },
    {
        "nurse_id": "NRS-002",
        "shift_id": SHIFT_ID,
        "name": "RN David Park",
        "role": "Primary Nurse",
        "assigned_patients": ["P-10003", "P-10004"],
        "assigned_rooms": ["Floor2-215", "Floor1-102"],
        "shift_start": (NOW.replace(hour=22, minute=0, second=0) - timedelta(days=1)).isoformat(),
        "shift_end": NOW.replace(hour=6, minute=0, second=0).isoformat(),
        "status": "active",
    },
    {
        "nurse_id": "NRS-003",
        "shift_id": SHIFT_ID,
        "name": "RN Sarah Johnson",
        "role": "Primary Nurse",
        "assigned_patients": ["P-10005"],
        "assigned_rooms": ["Floor1-118"],
        "shift_start": (NOW.replace(hour=22, minute=0, second=0) - timedelta(days=1)).isoformat(),
        "shift_end": NOW.replace(hour=6, minute=0, second=0).isoformat(),
        "status": "active",
    },
    {
        "nurse_id": "NRS-004",
        "shift_id": SHIFT_ID,
        "name": "RN Lisa Chen",
        "role": "Charge Nurse",
        "assigned_patients": ["P-10001", "P-10002", "P-10003", "P-10004", "P-10005"],
        "assigned_rooms": ["ICU-412", "Floor3-308", "Floor2-215", "Floor1-102", "Floor1-118"],
        "shift_start": (NOW.replace(hour=22, minute=0, second=0) - timedelta(days=1)).isoformat(),
        "shift_end": NOW.replace(hour=6, minute=0, second=0).isoformat(),
        "status": "active",
    },
    {
        "nurse_id": "NRS-005",
        "shift_id": SHIFT_ID,
        "name": "RN James Wilson",
        "role": "Backup Nurse",
        "assigned_patients": [],
        "assigned_rooms": [],
        "shift_start": (NOW.replace(hour=22, minute=0, second=0) - timedelta(days=1)).isoformat(),
        "shift_end": NOW.replace(hour=6, minute=0, second=0).isoformat(),
        "status": "active",
    },
]


def generate_alert_history():
    """Generate realistic alert history for the last 8 hours."""
    alerts = []
    base_time = NOW - timedelta(hours=8)

    alert_templates = [
        # P-10001 (critical patient) — generates many alerts
        {"patient_id": "P-10001", "alert_type": "vital_threshold", "severity": "MEDIUM", "detail": "Heart rate 112 bpm (threshold: 110)", "nurse_id": "NRS-001", "triage": "SUPPRESSED", "reason": "Within 2% of threshold, stable trend"},
        {"patient_id": "P-10001", "alert_type": "vital_threshold", "severity": "MEDIUM", "detail": "Heart rate 114 bpm (threshold: 110)", "nurse_id": "NRS-001", "triage": "SUPPRESSED", "reason": "Repeat alert, 3rd occurrence in 30 minutes"},
        {"patient_id": "P-10001", "alert_type": "vital_threshold", "severity": "HIGH", "detail": "BP systolic 82 mmHg (threshold: 85)", "nurse_id": "NRS-001", "triage": "ESCALATED", "reason": "Below critical threshold"},
        {"patient_id": "P-10001", "alert_type": "vital_threshold", "severity": "CRITICAL", "detail": "SpO2 88% (threshold: 92)", "nurse_id": "NRS-001", "triage": "ESCALATED", "reason": "Critical vital sign"},
        {"patient_id": "P-10001", "alert_type": "device_alarm", "severity": "LOW", "detail": "Monitor D-2001 connectivity intermittent", "nurse_id": "NRS-001", "triage": "SUPPRESSED", "reason": "Device D-2001 has known connectivity issues, 11.7% sensor drift"},
        {"patient_id": "P-10001", "alert_type": "device_alarm", "severity": "LOW", "detail": "Monitor D-2001 sensor recalibrating", "nurse_id": "NRS-001", "triage": "SUPPRESSED", "reason": "Device noise, auto-recalibration in progress"},
        {"patient_id": "P-10001", "alert_type": "repositioning", "severity": "MEDIUM", "detail": "3h since last repositioning", "nurse_id": "NRS-001", "triage": "BUNDLED", "reason": "Bundled with other P-10001 alerts"},
        {"patient_id": "P-10001", "alert_type": "fall_risk", "severity": "HIGH", "detail": "Bed exit detected at 2:14 AM", "nurse_id": "NRS-001", "triage": "ESCALATED", "reason": "High fall risk patient"},
        # P-10002 — moderate alerts
        {"patient_id": "P-10002", "alert_type": "repositioning", "severity": "MEDIUM", "detail": "2.5h since last repositioning", "nurse_id": "NRS-001", "triage": "BUNDLED", "reason": "Bundled with floor summary"},
        {"patient_id": "P-10002", "alert_type": "vital_threshold", "severity": "LOW", "detail": "Temperature 99.8F (threshold: 100)", "nurse_id": "NRS-001", "triage": "SUPPRESSED", "reason": "Below threshold, post-surgical baseline"},
        {"patient_id": "P-10002", "alert_type": "device_alarm", "severity": "LOW", "detail": "IV pump D-3002 battery low", "nurse_id": "NRS-001", "triage": "SUPPRESSED", "reason": "Informational, battery at 35%"},
        # P-10003 — few alerts
        {"patient_id": "P-10003", "alert_type": "vital_threshold", "severity": "MEDIUM", "detail": "Blood glucose 210 (threshold: 250)", "nurse_id": "NRS-002", "triage": "SUPPRESSED", "reason": "Within patient baseline for Type 1 Diabetes"},
        {"patient_id": "P-10003", "alert_type": "medication", "severity": "MEDIUM", "detail": "Insulin dose due in 15 minutes", "nurse_id": "NRS-002", "triage": "ESCALATED", "reason": "Medication reminder"},
        # P-10004 — minimal alerts (stable patient)
        {"patient_id": "P-10004", "alert_type": "vital_threshold", "severity": "LOW", "detail": "Heart rate 62 bpm (threshold: 60)", "nurse_id": "NRS-002", "triage": "SUPPRESSED", "reason": "Within 5% of threshold, patient sleeping"},
        # P-10005 — few alerts
        {"patient_id": "P-10005", "alert_type": "vital_threshold", "severity": "MEDIUM", "detail": "Temperature 100.2F (threshold: 101)", "nurse_id": "NRS-003", "triage": "SUPPRESSED", "reason": "Known pneumonia, expected low-grade fever"},
    ]

    for i, template in enumerate(alert_templates):
        offset_minutes = (i * 32) % (8 * 60)  # Spread across 8 hours
        alert_time = base_time + timedelta(minutes=offset_minutes)
        response_time = 120 if template["triage"] == "ESCALATED" else 0

        alerts.append({
            "alert_id": f"ALT-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": alert_time.isoformat(),
            "patient_id": template["patient_id"],
            "alert_type": template["alert_type"],
            "severity": template["severity"],
            "detail": template["detail"],
            "source_agent": "patient-monitoring",
            "triage_result": template["triage"],
            "suppression_reason": template.get("reason", ""),
            "assigned_nurse_id": template["nurse_id"],
            "acknowledged": template["triage"] == "ESCALATED",
            "acknowledged_at": (alert_time + timedelta(seconds=response_time)).isoformat() if template["triage"] == "ESCALATED" else "",
            "response_time_seconds": response_time if template["triage"] == "ESCALATED" else 0,
            "bundle_id": f"BDL-{template['patient_id']}" if template["triage"] == "BUNDLED" else "",
        })

    return alerts


def generate_nurse_workload():
    """Generate workload snapshots for each nurse."""
    workloads = []
    window_key = NOW.strftime("%Y-%m-%dT%H:00")

    nurse_stats = {
        "NRS-001": {"received": 22, "acknowledged": 8, "pending": 4, "suppressed": 18, "avg_response": 145, "load": 72},
        "NRS-002": {"received": 8, "acknowledged": 5, "pending": 1, "suppressed": 6, "avg_response": 95, "load": 35},
        "NRS-003": {"received": 4, "acknowledged": 3, "pending": 0, "suppressed": 3, "avg_response": 60, "load": 15},
        "NRS-004": {"received": 6, "acknowledged": 6, "pending": 0, "suppressed": 0, "avg_response": 30, "load": 20},
        "NRS-005": {"received": 0, "acknowledged": 0, "pending": 0, "suppressed": 0, "avg_response": 0, "load": 0},
    }

    for nurse_id, stats in nurse_stats.items():
        workloads.append({
            "nurse_id": nurse_id,
            "window_key": window_key,
            "alerts_received": stats["received"],
            "alerts_acknowledged": stats["acknowledged"],
            "alerts_pending": stats["pending"],
            "avg_response_time_seconds": stats["avg_response"],
            "cognitive_load_score": stats["load"],
            "suppressed_count": stats["suppressed"],
            "redirected_count": 0,
        })

    return workloads


ALERT_HISTORY = generate_alert_history()
NURSE_WORKLOAD = generate_nurse_workload()
