"""Patient Monitoring Agent - Configuration"""

import os

# AWS Configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_PATIENTS_TABLE = os.environ.get("DYNAMODB_PATIENTS_TABLE", "connected-care-patients")
DYNAMODB_VITALS_TABLE = os.environ.get("DYNAMODB_VITALS_TABLE", "connected-care-vitals")
EVENTBRIDGE_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")

# Agent Configuration
AGENT_MODEL = os.environ.get("AGENT_MODEL", "us.anthropic.claude-opus-4-6-v1")
AGENT_NAME = "Patient Monitoring Agent"

# Vital Sign Types
VITAL_SIGNS = {
    "heart_rate": {"unit": "bpm", "label": "Heart Rate"},
    "blood_pressure_systolic": {"unit": "mmHg", "label": "Blood Pressure (Systolic)"},
    "blood_pressure_diastolic": {"unit": "mmHg", "label": "Blood Pressure (Diastolic)"},
    "temperature": {"unit": "°F", "label": "Temperature"},
    "spo2": {"unit": "%", "label": "SpO2"},
    "respiratory_rate": {"unit": "breaths/min", "label": "Respiratory Rate"},
    "blood_glucose": {"unit": "mg/dL", "label": "Blood Glucose"},
}

# Normal Ranges (defaults, overridden by patient-specific thresholds)
NORMAL_RANGES = {
    "heart_rate": {"low": 60, "high": 100},
    "blood_pressure_systolic": {"low": 90, "high": 140},
    "blood_pressure_diastolic": {"low": 60, "high": 90},
    "temperature": {"low": 97.0, "high": 99.5},
    "spo2": {"low": 95, "high": 100},
    "respiratory_rate": {"low": 12, "high": 20},
    "blood_glucose": {"low": 70, "high": 140},
}

# Alert Severity Thresholds
CRITICAL_THRESHOLDS = {
    "heart_rate": {"low": 40, "high": 150},
    "blood_pressure_systolic": {"low": 70, "high": 180},
    "blood_pressure_diastolic": {"low": 40, "high": 120},
    "temperature": {"low": 95.0, "high": 104.0},
    "spo2": {"low": 88, "high": 100},
    "respiratory_rate": {"low": 8, "high": 30},
    "blood_glucose": {"low": 50, "high": 400},
}
