"""WF-06: Critical Shortage Patient Impact Assessment"""

WF06_CRITICAL_SHORTAGE_IMPACT = {
    "id": "WF-06",
    "name": "Critical Shortage Patient Impact Assessment",
    "description": "Identifies critical supply shortages, correlates with admitted patients, assesses clinical impact, checks for substitutes, and notifies care teams.",
    "steps": [
        {
            "step": 1,
            "agent": "inventory-management",
            "description": "Identify critical and high-risk stockout items",
            "prompt_template": "Check stockout risk across {floor}. List all items at CRITICAL or HIGH risk with their burn rates, hours until depletion, and dependent patients.",
        },
        {
            "step": 2,
            "agent": "patient-monitoring",
            "description": "Assess clinical status of affected patients",
            "prompt_template": "The following patients may be affected by supply shortages: {step_1_response}. For each patient, provide their current clinical status, risk profile, and how critical the affected supplies are to their care plan.",
        },
        {
            "step": 3,
            "agent": "inventory-management",
            "description": "Check substitute availability and cross-floor transfers",
            "prompt_template": "For the critical shortage items identified: {step_1_response}. Check if substitutes are available on the same floor or other floors. Assess feasibility of cross-floor transfers.",
        },
        {
            "step": 4,
            "agent": "device-management",
            "description": "Check device-supply dependencies",
            "prompt_template": "Supply shortages have been identified: {step_1_response}. Check if any of these items are consumables required by active medical devices (ventilator tubing, infusion pump sets, etc.). Which devices and patients would be affected if these supplies run out?",
        },
        {
            "step": 5,
            "agent": "patient-engagement",
            "description": "Notify care teams with prioritized action plan",
            "prompt_template": "Critical supply shortages are affecting patient care. Patient impact: {step_2_response}. Substitute availability: {step_3_response}. Device dependencies: {step_4_response}. Notify the affected care teams with a prioritized action plan — which patients need immediate attention and what alternatives are available.",
        },
    ],
}
