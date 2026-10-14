"""
Device Telemetry Simulator — Lambda Handler

Generates realistic synthetic device telemetry for 15 simulated medical devices
and writes to DynamoDB. Triggered automatically by CloudWatch Events schedule.
"""

import json
import os
import random
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
telemetry_table = dynamodb.Table(
    os.environ.get("DYNAMODB_DEVICE_TELEMETRY_TABLE", "connected-care-device-telemetry")
)

# Simulation profiles: define how each device's telemetry behaves
SIMULATION_PROFILES = {
    # === CRITICAL DEVICES (degrading) ===
    "D-2001": {  # Vital Signs Monitor — ICU-412
        "risk_profile": "critical",
        "battery_level": {"base": 22, "drift": -0.3, "noise": 2},
        "sensor_accuracy": {"base": 88, "drift": -0.15, "noise": 1.5},
        "error_count": {"base": 47, "drift": 0.5, "noise": 2},
        "uptime_hours": {"base": 18200, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 4.8, "drift": 0.08, "noise": 0.3},
        "device_temperature": {"base": 42, "drift": 0.05, "noise": 1},
        "memory_usage": {"base": 78, "drift": 0.1, "noise": 2},
        "signal_strength": {"base": -62, "drift": -0.1, "noise": 3},
        "usage_cycles": {"base": 9500, "drift": 1, "noise": 0},
        "connectivity": "intermittent",
    },
    "D-3001": {  # Infusion Pump — ICU-412
        "risk_profile": "critical",
        "battery_level": {"base": 18, "drift": -0.4, "noise": 2},
        "sensor_accuracy": {"base": 85, "drift": -0.2, "noise": 2},
        "error_count": {"base": 63, "drift": 0.8, "noise": 3},
        "uptime_hours": {"base": 22100, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 5.5, "drift": 0.1, "noise": 0.4},
        "device_temperature": {"base": 44, "drift": 0.08, "noise": 1.5},
        "memory_usage": {"base": 82, "drift": 0.15, "noise": 2},
        "signal_strength": {"base": -58, "drift": -0.05, "noise": 2},
        "usage_cycles": {"base": 12300, "drift": 1, "noise": 0},
        "connectivity": "intermittent",
    },
    "D-4001": {  # Ventilator — ICU-412
        "risk_profile": "critical",
        "battery_level": {"base": 30, "drift": -0.2, "noise": 2},
        "sensor_accuracy": {"base": 90, "drift": -0.1, "noise": 1},
        "error_count": {"base": 38, "drift": 0.4, "noise": 2},
        "uptime_hours": {"base": 25600, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 6.2, "drift": 0.12, "noise": 0.5},
        "device_temperature": {"base": 40, "drift": 0.03, "noise": 1},
        "memory_usage": {"base": 71, "drift": 0.08, "noise": 2},
        "signal_strength": {"base": -55, "drift": 0, "noise": 2},
        "usage_cycles": {"base": 15800, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    # === MODERATE DEVICES ===
    "D-2002": {  # Vital Signs Monitor — Floor3-308
        "risk_profile": "moderate",
        "battery_level": {"base": 55, "drift": -0.05, "noise": 3},
        "sensor_accuracy": {"base": 94, "drift": 0, "noise": 1},
        "error_count": {"base": 12, "drift": 0.1, "noise": 1},
        "uptime_hours": {"base": 11200, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 2.1, "drift": 0.02, "noise": 0.2},
        "device_temperature": {"base": 37, "drift": 0, "noise": 1},
        "memory_usage": {"base": 55, "drift": 0.02, "noise": 2},
        "signal_strength": {"base": -48, "drift": 0, "noise": 3},
        "usage_cycles": {"base": 5600, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-3002": {  # Infusion Pump — Floor2-215
        "risk_profile": "moderate",
        "battery_level": {"base": 48, "drift": -0.08, "noise": 3},
        "sensor_accuracy": {"base": 93, "drift": 0, "noise": 1.5},
        "error_count": {"base": 18, "drift": 0.15, "noise": 2},
        "uptime_hours": {"base": 8900, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 2.5, "drift": 0.03, "noise": 0.3},
        "device_temperature": {"base": 38, "drift": 0, "noise": 1},
        "memory_usage": {"base": 60, "drift": 0.03, "noise": 2},
        "signal_strength": {"base": -52, "drift": 0, "noise": 3},
        "usage_cycles": {"base": 4200, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-4002": {  # Ventilator — Floor3-310
        "risk_profile": "moderate",
        "battery_level": {"base": 62, "drift": -0.03, "noise": 2},
        "sensor_accuracy": {"base": 95, "drift": 0, "noise": 1},
        "error_count": {"base": 8, "drift": 0.05, "noise": 1},
        "uptime_hours": {"base": 7500, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 1.8, "drift": 0.01, "noise": 0.2},
        "device_temperature": {"base": 36, "drift": 0, "noise": 1},
        "memory_usage": {"base": 45, "drift": 0.01, "noise": 2},
        "signal_strength": {"base": -45, "drift": 0, "noise": 2},
        "usage_cycles": {"base": 3100, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-5002": {  # Wearable — Floor2-215
        "risk_profile": "moderate",
        "battery_level": {"base": 42, "drift": -0.1, "noise": 3},
        "sensor_accuracy": {"base": 92, "drift": 0, "noise": 2},
        "error_count": {"base": 5, "drift": 0.05, "noise": 1},
        "uptime_hours": {"base": 6200, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 1.5, "drift": 0.02, "noise": 0.2},
        "device_temperature": {"base": 34, "drift": 0, "noise": 1},
        "memory_usage": {"base": 38, "drift": 0.02, "noise": 2},
        "signal_strength": {"base": -58, "drift": -0.05, "noise": 4},
        "usage_cycles": {"base": 2800, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-6002": {  # Smart Home Sensor — Floor1-118
        "risk_profile": "moderate",
        "battery_level": {"base": 50, "drift": -0.06, "noise": 2},
        "sensor_accuracy": {"base": 94, "drift": 0, "noise": 1},
        "error_count": {"base": 3, "drift": 0.03, "noise": 1},
        "uptime_hours": {"base": 9800, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 1.2, "drift": 0.01, "noise": 0.15},
        "device_temperature": {"base": 30, "drift": 0, "noise": 1},
        "memory_usage": {"base": 32, "drift": 0.01, "noise": 2},
        "signal_strength": {"base": -50, "drift": 0, "noise": 3},
        "usage_cycles": {"base": 4500, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    # === HEALTHY DEVICES ===
    "D-2003": {  # Vital Signs Monitor — Floor1-102
        "risk_profile": "healthy",
        "battery_level": {"base": 92, "drift": -0.01, "noise": 1},
        "sensor_accuracy": {"base": 99, "drift": 0, "noise": 0.3},
        "error_count": {"base": 1, "drift": 0, "noise": 0.5},
        "uptime_hours": {"base": 4200, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 0.3, "drift": 0, "noise": 0.1},
        "device_temperature": {"base": 35, "drift": 0, "noise": 0.5},
        "memory_usage": {"base": 28, "drift": 0, "noise": 1},
        "signal_strength": {"base": -38, "drift": 0, "noise": 2},
        "usage_cycles": {"base": 1800, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-3003": {  # Infusion Pump — Floor1-118
        "risk_profile": "healthy",
        "battery_level": {"base": 88, "drift": -0.01, "noise": 1},
        "sensor_accuracy": {"base": 98, "drift": 0, "noise": 0.5},
        "error_count": {"base": 0, "drift": 0, "noise": 0.3},
        "uptime_hours": {"base": 3100, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 0.2, "drift": 0, "noise": 0.1},
        "device_temperature": {"base": 34, "drift": 0, "noise": 0.5},
        "memory_usage": {"base": 22, "drift": 0, "noise": 1},
        "signal_strength": {"base": -35, "drift": 0, "noise": 2},
        "usage_cycles": {"base": 1200, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-4003": {  # Ventilator — Floor2-220
        "risk_profile": "healthy",
        "battery_level": {"base": 95, "drift": -0.01, "noise": 1},
        "sensor_accuracy": {"base": 99, "drift": 0, "noise": 0.2},
        "error_count": {"base": 0, "drift": 0, "noise": 0.2},
        "uptime_hours": {"base": 2400, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 0.1, "drift": 0, "noise": 0.05},
        "device_temperature": {"base": 35, "drift": 0, "noise": 0.5},
        "memory_usage": {"base": 20, "drift": 0, "noise": 1},
        "signal_strength": {"base": -40, "drift": 0, "noise": 2},
        "usage_cycles": {"base": 900, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-5001": {  # Wearable — Floor3-308
        "risk_profile": "healthy",
        "battery_level": {"base": 78, "drift": -0.02, "noise": 2},
        "sensor_accuracy": {"base": 97, "drift": 0, "noise": 0.5},
        "error_count": {"base": 1, "drift": 0, "noise": 0.5},
        "uptime_hours": {"base": 5100, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 0.5, "drift": 0, "noise": 0.1},
        "device_temperature": {"base": 33, "drift": 0, "noise": 0.5},
        "memory_usage": {"base": 25, "drift": 0, "noise": 1},
        "signal_strength": {"base": -42, "drift": 0, "noise": 3},
        "usage_cycles": {"base": 2200, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-5003": {  # Wearable — Floor1-102
        "risk_profile": "healthy",
        "battery_level": {"base": 85, "drift": -0.01, "noise": 1},
        "sensor_accuracy": {"base": 98, "drift": 0, "noise": 0.3},
        "error_count": {"base": 0, "drift": 0, "noise": 0.3},
        "uptime_hours": {"base": 3600, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 0.2, "drift": 0, "noise": 0.08},
        "device_temperature": {"base": 32, "drift": 0, "noise": 0.5},
        "memory_usage": {"base": 18, "drift": 0, "noise": 1},
        "signal_strength": {"base": -36, "drift": 0, "noise": 2},
        "usage_cycles": {"base": 1500, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-6001": {  # Smart Home Sensor — Floor1-102
        "risk_profile": "healthy",
        "battery_level": {"base": 80, "drift": -0.02, "noise": 1},
        "sensor_accuracy": {"base": 97, "drift": 0, "noise": 0.5},
        "error_count": {"base": 0, "drift": 0, "noise": 0.3},
        "uptime_hours": {"base": 7200, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 0.4, "drift": 0, "noise": 0.1},
        "device_temperature": {"base": 28, "drift": 0, "noise": 0.5},
        "memory_usage": {"base": 15, "drift": 0, "noise": 1},
        "signal_strength": {"base": -40, "drift": 0, "noise": 2},
        "usage_cycles": {"base": 3200, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
    "D-6003": {  # Smart Home Sensor — Floor3-310
        "risk_profile": "healthy",
        "battery_level": {"base": 90, "drift": -0.01, "noise": 1},
        "sensor_accuracy": {"base": 98, "drift": 0, "noise": 0.3},
        "error_count": {"base": 0, "drift": 0, "noise": 0.2},
        "uptime_hours": {"base": 2800, "drift": 1, "noise": 0},
        "calibration_drift": {"base": 0.15, "drift": 0, "noise": 0.05},
        "device_temperature": {"base": 27, "drift": 0, "noise": 0.5},
        "memory_usage": {"base": 12, "drift": 0, "noise": 1},
        "signal_strength": {"base": -38, "drift": 0, "noise": 2},
        "usage_cycles": {"base": 1100, "drift": 1, "noise": 0},
        "connectivity": "connected",
    },
}


# Telemetry metric clamps (min, max)
METRIC_CLAMPS = {
    "battery_level": (0, 100),
    "sensor_accuracy": (50, 100),
    "error_count": (0, 999),
    "uptime_hours": (0, 99999),
    "calibration_drift": (0, 20),
    "device_temperature": (15, 65),
    "memory_usage": (0, 100),
    "signal_strength": (-100, -20),
    "usage_cycles": (0, 99999),
}

CONNECTIVITY_OPTIONS = ["connected", "intermittent", "disconnected"]


def generate_metric(profile: dict, metric_name: str) -> Decimal:
    """Generate a single telemetry metric with drift and noise."""
    cfg = profile[metric_name]
    value = cfg["base"] + cfg["drift"] + random.gauss(0, cfg["noise"])
    cfg["base"] = cfg["base"] + cfg["drift"]

    low, high = METRIC_CLAMPS.get(metric_name, (0, 99999))
    value = max(low, min(high, value))

    if metric_name in ("calibration_drift", "device_temperature"):
        return Decimal(str(round(value, 1)))
    return Decimal(str(round(value)))


def generate_connectivity(profile: dict) -> str:
    """Generate connectivity status based on risk profile."""
    base = profile.get("connectivity", "connected")
    if base == "intermittent":
        return random.choice(["connected", "connected", "intermittent", "disconnected"])
    if base == "disconnected":
        return random.choice(["disconnected", "disconnected", "intermittent"])
    return "connected"


def handler(event, context):
    """Lambda handler — generates telemetry for all devices and writes to DynamoDB."""
    timestamp = datetime.now(timezone.utc).isoformat()
    records_written = 0

    numeric_metrics = [
        "battery_level", "sensor_accuracy", "error_count", "uptime_hours",
        "calibration_drift", "device_temperature", "memory_usage",
        "signal_strength", "usage_cycles",
    ]

    for device_id, profile in SIMULATION_PROFILES.items():
        telemetry = {}
        for metric in numeric_metrics:
            telemetry[metric] = generate_metric(profile, metric)

        telemetry["connectivity_status"] = generate_connectivity(profile)
        telemetry["firmware_version"] = profile.get("firmware_version", "unknown")

        item = {
            "device_id": device_id,
            "timestamp": timestamp,
            "reading_id": str(uuid.uuid4()),
            "telemetry": telemetry,
            "risk_profile": profile["risk_profile"],
        }

        telemetry_table.put_item(Item=item)
        records_written += 1

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Generated telemetry for {records_written} devices",
            "timestamp": timestamp,
        }),
    }
