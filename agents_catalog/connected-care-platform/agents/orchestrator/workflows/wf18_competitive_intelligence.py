"""WF-18: Competitive Intelligence Assessment"""

WF18_COMPETITIVE_INTELLIGENCE = {
    "id": "WF-18",
    "name": "Competitive Intelligence Assessment",
    "description": "Detects early signals that hospital accounts may be evaluating competitor devices by analyzing utilization trends, firmware update deferrals, consumable ordering patterns, and service friction.",
    "steps": [
        {
            "step": 1,
            "agent": "field-service",
            "description": "Analyze device utilization and firmware compliance across all sites",
            "prompt_template": "Analyze the installed base across all hospital sites. For each site, report: device utilization trends (are devices being used less?), firmware compliance (are updates being deferred?), and any devices that have been taken offline or decommissioned recently. Flag sites with declining engagement.",
        },
        {
            "step": 2,
            "agent": "field-service",
            "description": "Review service history for friction signals",
            "prompt_template": "Review the service history across all sites. Look for friction signals: deferred firmware updates, partial service outcomes, billable visits that caused pushback, or sites that declined recommended maintenance. These are early indicators of dissatisfaction. Sites with friction: {step_1_response}.",
        },
        {
            "step": 3,
            "agent": "account-intelligence",
            "description": "Assess account health and contract risk for flagged accounts",
            "prompt_template": "These accounts are showing potential competitive evaluation signals: {step_1_response}. Service friction: {step_2_response}. For each flagged account, pull the full health score, contract status, and renewal timeline. Identify which accounts are most at risk of switching to a competitor.",
        },
        {
            "step": 4,
            "agent": "account-intelligence",
            "description": "Generate competitive response strategy",
            "prompt_template": "Based on utilization decline: {step_1_response}, service friction: {step_2_response}, and account risk: {step_3_response}. Generate a competitive response strategy for each at-risk account. What specific actions should the sales team take? What value can we demonstrate? What executive engagement is needed? Prioritize by revenue at risk.",
        },
    ],
}
