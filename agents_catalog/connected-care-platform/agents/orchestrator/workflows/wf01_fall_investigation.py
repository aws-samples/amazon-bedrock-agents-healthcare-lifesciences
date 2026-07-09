"""WF-01: Fall Detection & Root Cause Investigation"""

WF01_FALL_INVESTIGATION = {
    "id": "WF-01",
    "name": "Fall Detection & Root Cause Investigation",
    "description": "Coordinates fall confirmation, device diagnostics, clinical context, and care response across all three agents.",
    "steps": [
        {
            "step": 1,
            "agent": "patient-monitoring",
            "description": "Confirm fall event and classify severity",
            "prompt_template": "Patient {patient_id} experienced a fall event in {location}. First recall their AgentCore Memory for fall risk factors, recent medication changes (especially those causing dizziness or orthostatic hypotension), and any prior fall-related observations. Then confirm the fall using available sensor data, classify the severity (stumble/moderate/hard fall), and provide a vital signs snapshot at the time of the event.",
        },
        {
            "step": 2,
            "agent": "device-management",
            "description": "Retrieve device diagnostics at time of fall",
            "prompt_template": "Check all devices in {location} at the time of the fall event. Report battery levels, sensor accuracy, calibration status, and any recent false positive history for each device.",
        },
        {
            "step": 3,
            "agent": "device-management",
            "description": "Check nearby sensors for corroborating data",
            "prompt_template": "Check all nearby sensors in {location} for corroborating data around the time of the fall. Include bed sensors, floor mats, and room monitors.",
        },
        {
            "step": 4,
            "agent": "patient-monitoring",
            "description": "Analyze pre-fall clinical context",
            "prompt_template": "Analyze the clinical context for patient {patient_id} in the 2 hours before the fall. Include vital sign trends, recent medication events, and any relevant clinical observations.",
        },
        {
            "step": 5,
            "agent": "patient-engagement",
            "description": "Execute fall response protocol",
            "prompt_template": "Execute the fall response protocol for patient {patient_id}. The fall severity is: {previous_findings}. Send notifications to the care team, alert the emergency contact, create an incident report, and schedule a follow-up assessment.",
        },
    ],
}
