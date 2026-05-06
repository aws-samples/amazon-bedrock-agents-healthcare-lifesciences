"""Device Management Agent — Configuration"""

import os

# AWS Configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_DEVICES_TABLE = os.environ.get("DYNAMODB_DEVICES_TABLE", "connected-care-devices")
DYNAMODB_DEVICE_TELEMETRY_TABLE = os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry")
DYNAMODB_DEVICE_ASSIGNMENTS_TABLE = os.environ.get("DYNAMODB_DEVICE_ASSIGNMENTS_TABLE", "connected-care-device-assignments")
DYNAMODB_WORK_ORDERS_TABLE = os.environ.get("DYNAMODB_WORK_ORDERS_TABLE", "connected-care-work-orders")
EVENTBRIDGE_BUS_NAME = os.environ.get("EVENTBRIDGE_BUS_NAME", "connected-care-events")

# Agent Configuration
AGENT_MODEL = os.environ.get("AGENT_MODEL", "us.anthropic.claude-opus-4-6-v1")
AGENT_NAME = "Device Management Agent"

# Device Types
DEVICE_TYPES = {
    "vital_signs_monitor": {"label": "Vital Signs Monitor", "category": "monitoring"},
    "infusion_pump": {"label": "Infusion Pump", "category": "therapeutic"},
    "ventilator": {"label": "Ventilator", "category": "life_support"},
    "wearable": {"label": "Wearable Sensor", "category": "monitoring"},
    "smart_home_sensor": {"label": "Smart Home Sensor", "category": "environmental"},
}

# Telemetry Metrics
TELEMETRY_METRICS = {
    "battery_level": {"unit": "%", "label": "Battery Level"},
    "connectivity_status": {"unit": "", "label": "Connectivity"},
    "sensor_accuracy": {"unit": "%", "label": "Sensor Accuracy"},
    "error_count": {"unit": "errors", "label": "Error Count"},
    "uptime_hours": {"unit": "hours", "label": "Uptime"},
    "firmware_version": {"unit": "", "label": "Firmware Version"},
    "calibration_drift": {"unit": "%", "label": "Calibration Drift"},
    "device_temperature": {"unit": "°C", "label": "Device Temperature"},
    "memory_usage": {"unit": "%", "label": "Memory Usage"},
    "signal_strength": {"unit": "dBm", "label": "Signal Strength"},
    "usage_cycles": {"unit": "cycles", "label": "Usage Cycles"},
}

# Alert Thresholds (trigger investigation)
ALERT_THRESHOLDS = {
    "battery_level": {"low": 20, "critical": 10},
    "sensor_accuracy": {"low": 90, "critical": 85},
    "error_count": {"high": 30, "critical": 50},
    "calibration_drift": {"high": 3.0, "critical": 5.0},
    "device_temperature": {"high": 45, "critical": 55},
    "memory_usage": {"high": 80, "critical": 90},
    "signal_strength": {"low": -70, "critical": -80},
}

# Device Status Options
DEVICE_STATUSES = ["active", "maintenance", "offline", "decommissioned"]

# Work Order Priorities
WORK_ORDER_PRIORITIES = ["low", "medium", "high", "critical"]
