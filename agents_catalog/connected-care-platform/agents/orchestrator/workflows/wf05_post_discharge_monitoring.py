"""WF-05: Post-Discharge Remote Monitoring Activation"""

WF05_POST_DISCHARGE_MONITORING = {
    "id": "WF-05",
    "name": "Post-Discharge Remote Monitoring Activation",
    "description": "Retrieves discharge plan, provisions devices, activates monitoring, and onboards the patient.",
    "steps": [
        {
            "step": 1,
            "agent": "patient-engagement",
            "description": "Retrieve discharge plan and patient preferences",
            "prompt_template": "Patient {patient_id} is being discharged. Retrieve their discharge plan including conditions to monitor, prescribed medications, follow-up appointments, communication preferences, and tech comfort level.",
        },
        {
            "step": 2,
            "agent": "device-management",
            "description": "Provision and configure home monitoring devices",
            "prompt_template": "Patient {patient_id} is being discharged and needs home monitoring devices. Based on the discharge plan: {step_1_response}. Find appropriate devices, assign them to the patient, and verify readiness.",
        },
        {
            "step": 3,
            "agent": "patient-monitoring",
            "description": "Activate personalized monitoring protocols",
            "prompt_template": "Patient {patient_id} is being discharged with home monitoring devices: {step_2_response}. Set up personalized alert thresholds based on their conditions and medications. Activate the monitoring protocol.",
        },
        {
            "step": 4,
            "agent": "patient-engagement",
            "description": "Onboard patient with training and welcome communication",
            "prompt_template": "Patient {patient_id} has been discharged with monitoring devices configured. Send a welcome message via their preferred channel, deliver device training materials appropriate for their age and tech comfort level, configure family caregiver access, and schedule the first check-in call.",
        },
    ],
}
