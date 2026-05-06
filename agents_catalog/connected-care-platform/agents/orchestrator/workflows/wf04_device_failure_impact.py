"""WF-04: Device Failure Patient Impact Assessment"""

WF04_DEVICE_FAILURE_IMPACT = {
    "id": "WF-04",
    "name": "Device Failure Patient Impact Assessment",
    "description": "Assesses which patients are affected by a device failure, evaluates clinical risk, locates replacements, and notifies care teams.",
    "steps": [
        {
            "step": 1,
            "agent": "device-management",
            "description": "Identify failed device and assess failure scope",
            "prompt_template": "Device {device_id} has failed. Identify the device type, location, and classify the failure (hardware/software/connectivity). Assess the scope of the failure.",
        },
        {
            "step": 2,
            "agent": "patient-monitoring",
            "description": "Identify patients dependent on this device",
            "prompt_template": "A {device_type} in {location} has failed. Which patients in that location are being monitored? What is each patient's current clinical status and how dependent are they on this device type?",
        },
        {
            "step": 3,
            "agent": "patient-monitoring",
            "description": "Assess clinical risk of the monitoring gap",
            "prompt_template": "The following patients have lost monitoring due to a device failure: {step_2_response}. For each patient, assess the clinical risk of the monitoring gap. How long can each patient safely go without this monitoring?",
        },
        {
            "step": 4,
            "agent": "device-management",
            "description": "Locate replacement devices and assess readiness",
            "prompt_template": "We need a replacement {device_type} for {location}. Find all available replacement devices of this type, their locations, and readiness status (battery, calibration, firmware). Estimate deployment time.",
        },
        {
            "step": 5,
            "agent": "patient-engagement",
            "description": "Notify care teams with patient-specific assessments",
            "prompt_template": "A device failure in {location} is affecting patients. Patient impact: {step_3_response}. Replacement availability: {step_4_response}. Notify the affected care teams with per-patient risk assessments and replacement logistics.",
        },
    ],
}
