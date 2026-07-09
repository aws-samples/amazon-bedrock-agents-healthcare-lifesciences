"""WF-17: Proactive Contract Renewal Package"""

WF17_RENEWAL_PACKAGE = {
    "id": "WF-17",
    "name": "Proactive Contract Renewal Package",
    "description": "Auto-generates a comprehensive contract renewal package for a hospital account — fleet health, service value, consumable trends, and a data-driven case for renewal.",
    "steps": [
        {
            "step": 1,
            "agent": "account-intelligence",
            "description": "Pull account profile and contract status",
            "prompt_template": "Generate a comprehensive account summary for {site_id}. Include contract details, renewal date, health score, and all risk factors.",
        },
        {
            "step": 2,
            "agent": "field-service",
            "description": "Summarize fleet health and service value delivered",
            "prompt_template": "For the account at {site_id}: {step_1_response}. Summarize the installed device fleet — how many devices, their health status, firmware compliance. Then review the service history — how many preventive vs corrective visits, what issues were caught proactively, what parts were replaced. Quantify the value of proactive service.",
        },
        {
            "step": 3,
            "agent": "field-service",
            "description": "Compare firmware performance and identify upgrade value",
            "prompt_template": "For the devices at {site_id}, compare firmware performance. Are there devices on older firmware with higher error rates? Quantify the improvement the customer would see from firmware upgrades included in the service contract.",
        },
        {
            "step": 4,
            "agent": "account-intelligence",
            "description": "Generate renewal recommendation with risk of non-renewal",
            "prompt_template": "Based on account profile: {step_1_response}, fleet health and service value: {step_2_response}, and firmware analysis: {step_3_response}. Generate a contract renewal recommendation. Include: (1) value delivered during the current contract period, (2) what the hospital would lose without the contract, (3) recommended contract tier and pricing justification, (4) risk assessment if the customer does not renew.",
        },
    ],
}
