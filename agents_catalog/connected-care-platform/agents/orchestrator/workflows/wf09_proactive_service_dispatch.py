"""WF-09: Proactive Service Dispatch Planning"""

WF09_PROACTIVE_SERVICE_DISPATCH = {
    "id": "WF-09",
    "name": "Proactive Service Dispatch Planning",
    "description": "Scans the installed base for devices predicted to need service, checks parts availability, and creates an optimized FSE dispatch plan.",
    "steps": [
        {
            "step": 1,
            "agent": "field-service",
            "description": "Predict service needs across all sites",
            "prompt_template": "Predict which devices across all hospital sites will need field service in the next {days_ahead} days. Group results by hospital site.",
        },
        {
            "step": 2,
            "agent": "field-service",
            "description": "Get detailed telemetry for flagged devices",
            "prompt_template": "For the devices flagged for service: {step_1_response}. Get the detailed performance data for each device model involved. Compare firmware versions to identify if firmware updates would resolve the issues.",
        },
        {
            "step": 3,
            "agent": "inventory-management",
            "description": "Check parts and consumable availability",
            "prompt_template": "Field service visits are planned for these devices: {step_1_response}. Check if the required device consumables (tubing, sensors, calibration kits) are available at each hospital site.",
        },
        {
            "step": 4,
            "agent": "field-service",
            "description": "Create optimized dispatch plan",
            "prompt_template": "Based on service predictions: {step_1_response}, firmware analysis: {step_2_response}, and parts availability: {step_3_response}. Create an optimized FSE dispatch plan grouping nearby sites, prioritizing by severity, and listing parts to bring.",
        },
        {
            "step": 5,
            "agent": "account-intelligence",
            "description": "Flag accounts with upcoming renewals",
            "prompt_template": "Service dispatches are planned for these sites: {step_4_response}. Check if any of these accounts have upcoming contract renewals. Flag where service quality is especially important for retention.",
        },
    ],
}
