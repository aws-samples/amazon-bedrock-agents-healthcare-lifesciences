# Field Service Intelligence Agent — Sample Prompts

## Installed Base

- Show me the full installed base across all hospital customers
- What devices do we have at Riverside Community Hospital?
- How many devices are on outdated firmware across all sites?
- Show me the installed base for site-003

## Predictive Service

- Which devices across our hospitals need service in the next 14 days?
- What are the most critical devices needing attention right now?
- Predict field service needs for the next 30 days
- Which sites have the most devices at risk?

## Firmware Analysis

- Compare firmware performance for BD Alaris 8015 pumps
- How are Hamilton C6 ventilators performing across different firmware versions?
- Compare firmware performance for Philips IntelliVue MX800
- Which firmware version of BD Alaris has the highest error rate?

## Device Model Performance

- How are all BD Alaris 8015 pumps performing across our installed base?
- Show me fleet-wide performance data for Hamilton C6 ventilators
- Get aggregate reliability metrics for Philips IntelliVue MX800 across all sites
- Which device model has the worst error rates?

## Service History

- Show me the service history for Riverside Community Hospital
- What service visits have we done for device D-8005?
- Get the full service history for site-001
- How many corrective vs preventive visits have we done at Lakewood?

## Service Dispatch

- Create a service dispatch for Riverside Community Hospital to fix D-8003 and D-8005
- Plan a preventive maintenance visit to Lakewood Surgical Center for D-9003
- Schedule Mike Chen for a critical visit to site-002 to address the Hamilton C6 calibration drift

## Cross-Agent Workflows (via Orchestrator)

- Plan proactive service dispatches for all sites over the next 14 days (WF-09)
- Generate a post-market surveillance report for BD Alaris 8015 (WF-10)
- Which devices need service and do the sites have the parts in stock? (WF-09)
- Are there any safety signals emerging across our Hamilton C6 fleet? (WF-10)
