"""WF-10: Post-Market Surveillance Report"""

WF10_POST_MARKET_SURVEILLANCE = {
    "id": "WF-10",
    "name": "Post-Market Surveillance Report",
    "description": "Aggregates fleet-wide performance data for a device model, compares firmware versions, detects emerging quality signals, and generates a surveillance summary.",
    "steps": [
        {
            "step": 1,
            "agent": "field-service",
            "description": "Aggregate fleet performance for the model",
            "prompt_template": "Get the fleet-wide performance data for all {model} devices across all hospital sites. Include error rates, accuracy, calibration drift, and uptime by site.",
        },
        {
            "step": 2,
            "agent": "field-service",
            "description": "Compare firmware version performance",
            "prompt_template": "Compare the performance of {model} devices across different firmware versions. Identify if any firmware version has significantly worse error rates or accuracy.",
        },
        {
            "step": 3,
            "agent": "field-service",
            "description": "Review service history for patterns",
            "prompt_template": "Get the field service history for all {model} devices. Are there recurring failure patterns? Which sites have the most corrective visits for this model?",
        },
        {
            "step": 4,
            "agent": "account-intelligence",
            "description": "Assess customer impact of quality issues",
            "prompt_template": "Quality issues have been identified with {model} devices: {step_1_response}. Firmware analysis: {step_2_response}. Assess which customer accounts are most affected and whether this impacts any upcoming contract renewals.",
        },
    ],
}
