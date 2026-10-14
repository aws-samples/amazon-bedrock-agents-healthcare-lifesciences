"""WF-03: Patient Deterioration Cascade"""

WF03_DETERIORATION_CASCADE = {
    "id": "WF-03",
    "name": "Patient Deterioration Cascade",
    "description": "Validates deterioration is real (not a device issue), gathers clinical context, and activates rapid response.",
    "steps": [
        {
            "step": 1,
            "agent": "patient-monitoring",
            "description": "Provide deterioration trajectory with memory context",
            "prompt_template": "Patient {patient_id} has triggered a deterioration early warning. First recall their AgentCore Memory for recent clinical observations, medication changes, and treatment responses. Then provide the deterioration trajectory: which vitals are declining, rate of change, predicted time to critical threshold, and whether any recent medication changes or clinical events from memory could explain the deterioration.",
        },
        {
            "step": 2,
            "agent": "device-management",
            "description": "Verify all monitoring devices are functioning",
            "prompt_template": "Verify all monitoring devices assigned to or near patient {patient_id}. Check sensor accuracy, calibration status, and connectivity. Confirm the vital sign readings are from reliable devices.",
        },
        {
            "step": 3,
            "agent": "patient-monitoring",
            "description": "Assemble full clinical context from memory and records",
            "prompt_template": "Assemble the full clinical context for patient {patient_id}: recall all AgentCore Memory observations, active conditions, current medications, recent medication responses, recent procedures, allergies, and the latest clinical assessment. Include any unstructured observations from nurses or clinicians stored in memory. This is for a rapid response briefing — the responding team needs the complete picture.",
        },
        {
            "step": 4,
            "agent": "patient-engagement",
            "description": "Activate rapid response protocol",
            "prompt_template": "Activate the rapid response protocol for patient {patient_id}. Deterioration assessment: {step_1_response}. Device verification: {step_2_response}. Clinical context: {step_3_response}. Page the care team, pre-order relevant labs, and notify the family if patient preferences allow.",
        },
    ],
}
