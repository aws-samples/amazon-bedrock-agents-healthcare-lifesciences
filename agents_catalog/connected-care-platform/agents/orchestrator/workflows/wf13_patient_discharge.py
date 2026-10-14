"""WF-13: Patient Discharge with Memory Export and Cleanup"""

WF13_PATIENT_DISCHARGE = {
    "id": "WF-15",
    "name": "Patient Discharge with Memory Cleanup",
    "description": "Assesses discharge readiness using patient memory, generates a discharge summary from the full timeline, verifies discharge supplies, and clears patient memory.",
    "steps": [
        {
            "step": 1,
            "agent": "patient-monitoring",
            "description": "Assess discharge readiness from memory timeline",
            "prompt_template": "Assess discharge readiness for patient {patient_id}. Recall their full AgentCore Memory — review all clinical observations, medication responses, treatment trajectory, and unresolved concerns recorded during the stay. Combine this with current vitals stability to provide a comprehensive readiness assessment.",
        },
        {
            "step": 2,
            "agent": "patient-engagement",
            "description": "Review discharge plan and care coordination",
            "prompt_template": "Patient {patient_id} is being evaluated for discharge. Readiness assessment: {step_1_response}. Review the discharge plan, upcoming follow-up appointments, and medication instructions.",
        },
        {
            "step": 3,
            "agent": "inventory-management",
            "description": "Verify discharge supplies are available",
            "prompt_template": "Patient {patient_id} is being discharged. Check if discharge supply kits and take-home medications are available on the floor.",
        },
        {
            "step": 4,
            "agent": "patient-monitoring",
            "description": "Generate discharge summary and clear memory",
            "prompt_template": "Patient {patient_id} is confirmed for discharge. Get their full patient timeline to compile the discharge summary, then clear the patient memory. Include all clinical observations, medication changes, and treatment responses in the summary.",
        },
    ],
}
