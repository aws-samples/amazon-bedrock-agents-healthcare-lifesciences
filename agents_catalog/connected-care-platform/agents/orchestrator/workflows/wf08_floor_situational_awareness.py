"""WF-08: Floor Situational Awareness Briefing"""

WF08_FLOOR_SITUATIONAL_AWARENESS = {
    "id": "WF-08",
    "name": "Floor Situational Awareness Briefing",
    "description": "Generates a comprehensive floor status briefing combining patient acuity with AgentCore Memory insights, device health, supply levels, and staffing to give charge nurses a prioritized action list.",
    "steps": [
        {
            "step": 1,
            "agent": "patient-monitoring",
            "description": "Patient acuity, clinical status, and memory-enriched context",
            "prompt_template": "Provide a floor status summary for {floor}. For EACH patient: list their current risk profile, active alerts, deterioration trends, AND recall their AgentCore Memory for recent clinical observations, medication responses, and unresolved concerns. The shift handoff needs the full picture — not just vitals, but what has happened to each patient during the previous shift.",
        },
        {
            "step": 2,
            "agent": "device-management",
            "description": "Device health and availability summary",
            "prompt_template": "Provide a device status summary for {floor}. List all devices, their health status, any devices in maintenance or at risk of failure, and current device-to-patient assignments. Flag any monitoring gaps.",
        },
        {
            "step": 3,
            "agent": "inventory-management",
            "description": "Supply levels and stockout risk summary",
            "prompt_template": "Provide an inventory status summary for {floor}. List all items at risk of stockout, their hours until depletion, affected patients, and any pending reorders. Highlight items with no substitutes available.",
        },
        {
            "step": 4,
            "agent": "patient-engagement",
            "description": "Staffing, workload, and pending actions summary",
            "prompt_template": "Provide a care team and workload summary for {floor}. Include nurse alert loads, pending discharges, upcoming appointments, and any communication actions needed. Patient context: {step_1_response}. Supply issues: {step_3_response}.",
        },
    ],
}
