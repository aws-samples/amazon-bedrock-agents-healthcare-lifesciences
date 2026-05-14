"""WF-07: Admission Supply Readiness Check"""

WF07_ADMISSION_READINESS = {
    "id": "WF-07",
    "name": "Admission Supply Readiness Check",
    "description": "Verifies that all required supplies, medications, and device consumables are available on the floor before or during a new patient admission.",
    "steps": [
        {
            "step": 1,
            "agent": "patient-monitoring",
            "description": "Get patient profile and care requirements",
            "prompt_template": "Patient {patient_id} is being admitted to {floor}. Provide their full clinical profile including conditions, medications, monitoring requirements, and any special care needs.",
        },
        {
            "step": 2,
            "agent": "inventory-management",
            "description": "Check supply availability for patient needs",
            "prompt_template": "A patient is being admitted to {floor} with these care requirements: {step_1_response}. Check if all required medications, consumables, and supplies are available on the floor. Flag any items that are low or at risk of stockout.",
        },
        {
            "step": 3,
            "agent": "device-management",
            "description": "Verify device and equipment readiness",
            "prompt_template": "A patient is being admitted to {floor} with these care requirements: {step_1_response}. Check device availability — are the required monitoring devices, infusion pumps, or other equipment available and in working condition? Are the consumables for those devices in stock?",
        },
        {
            "step": 4,
            "agent": "inventory-management",
            "description": "Create reorder requests for any gaps",
            "prompt_template": "Based on the admission readiness check — supply gaps: {step_2_response}, device gaps: {step_3_response}. For any missing or low items, create appropriate reorder requests. Summarize the admission readiness status: READY, READY WITH CAVEATS, or NOT READY.",
        },
    ],
}
