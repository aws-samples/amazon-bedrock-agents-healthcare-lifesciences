"""WF-16: Regulatory Recall Impact Assessment"""

WF16_RECALL_IMPACT = {
    "id": "WF-16",
    "name": "Regulatory Recall Impact Assessment",
    "description": "When a field safety notice or recall is issued, identifies every affected device across all hospital customers, assesses patient impact, checks replacement parts, and generates a prioritized recall response plan.",
    "steps": [
        {
            "step": 1,
            "agent": "field-service",
            "description": "Identify all affected devices across the installed base",
            "prompt_template": "A safety recall has been issued for {model} devices on firmware {firmware_version}. Search the entire installed base across all hospital sites. List every affected device with its location, site, current status, and risk profile. Group by hospital.",
        },
        {
            "step": 2,
            "agent": "field-service",
            "description": "Assess device performance and failure risk for affected units",
            "prompt_template": "For the recalled devices identified: {step_1_response}. Get the detailed performance data — error counts, calibration drift, sensor accuracy. Which devices are most at risk of the recalled issue? Prioritize by severity.",
        },
        {
            "step": 3,
            "agent": "inventory-management",
            "description": "Check replacement parts and consumable availability",
            "prompt_template": "A device recall requires field service visits to these sites: {step_1_response}. Check if replacement parts, firmware update kits, and device consumables are available at each affected hospital. Flag any supply gaps that would delay the recall response.",
        },
        {
            "step": 4,
            "agent": "field-service",
            "description": "Create prioritized recall response dispatch plan",
            "prompt_template": "Based on affected devices: {step_1_response}, risk assessment: {step_2_response}, and parts availability: {step_3_response}. Create a prioritized recall response plan — which sites to visit first, which FSEs to assign, what parts to bring, and estimated timeline to complete the recall across all sites.",
        },
        {
            "step": 5,
            "agent": "account-intelligence",
            "description": "Assess customer relationship impact of the recall",
            "prompt_template": "A device recall is affecting these hospital accounts: {step_1_response}. Recall response plan: {step_4_response}. For each affected account, assess the relationship impact — are any of these accounts at risk of churn? Do any have upcoming contract renewals? Recommend proactive communication strategies to maintain trust.",
        },
    ],
}
