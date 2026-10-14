"""WF-11: Account Health Review"""

WF11_ACCOUNT_HEALTH_REVIEW = {
    "id": "WF-11",
    "name": "Account Health Review",
    "description": "Calculates health scores for all accounts, identifies at-risk customers, reviews service history and supply trends, and generates a prioritized action plan.",
    "steps": [
        {
            "step": 1,
            "agent": "account-intelligence",
            "description": "Calculate health scores for all accounts",
            "prompt_template": "Calculate account health scores for all hospital customers. Include device utilization, service trends, contract status, and firmware compliance.",
        },
        {
            "step": 2,
            "agent": "field-service",
            "description": "Review service history for at-risk accounts",
            "prompt_template": "These accounts are at risk: {step_1_response}. Get the recent service history for each at-risk account. Are there unresolved issues or deferred maintenance?",
        },
        {
            "step": 3,
            "agent": "account-intelligence",
            "description": "Assess contract renewal risk",
            "prompt_template": "Review contract renewal risk for all accounts. Cross-reference with the health scores: {step_1_response} and service issues: {step_2_response}.",
        },
        {
            "step": 4,
            "agent": "account-intelligence",
            "description": "Generate prioritized action plan",
            "prompt_template": "Based on health scores: {step_1_response}, service issues: {step_2_response}, and renewal risks: {step_3_response}. Generate a prioritized action plan for the commercial team — which accounts need immediate attention and what specific actions should be taken.",
        },
    ],
}
