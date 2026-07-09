# Connected Care Platform — Workflow Reference

## Clinical Workflows — Cross-Module

**WF-01: Fall Detection & Investigation** (5 steps | Patient Monitoring + Device Management + Patient Engagement)
Confirms a fall event using sensor data, correlates device diagnostics and medication history from AgentCore Memory, analyzes contributing clinical factors like orthostatic hypotension, and initiates an automated care response with care team notification.

**WF-02: Medication-Vitals Correlation** (5 steps | Patient Monitoring + Patient Engagement + Device Management)
Investigates whether an unexpected vital sign change was caused by a medication change or a device malfunction. Cross-references recent medication adjustments with vital sign trends and device calibration status to identify the root cause.

**WF-03: Patient Deterioration Cascade** (4 steps | Patient Monitoring + Device Management + Patient Engagement)
Validates that deterioration is real (not a device artifact), recalls the patient's AgentCore Memory for recent medication responses and clinical observations, assembles the full clinical context, and activates rapid response with pre-assembled information so the care team arrives already informed.

**WF-04: Device Failure Patient Impact** (5 steps | Device Management + Patient Monitoring + Patient Engagement)
When a device fails, identifies which patients are affected, evaluates the clinical risk of the monitoring gap for each patient, locates replacement devices and assesses their readiness, and notifies care teams with patient-specific risk assessments.

**WF-05: Post-Discharge Monitoring** (4 steps | Patient Engagement + Device Management + Patient Monitoring)
Retrieves the discharge plan, provisions home monitoring devices, activates personalized monitoring protocols based on the patient's conditions, and onboards the patient with communication preferences and follow-up scheduling.

**WF-06: Critical Shortage Patient Impact** (5 steps | Inventory Management + Patient Monitoring + Device Management + Patient Engagement)
Identifies critical supply shortages on a hospital floor, cross-references low-stock items with admitted patients' medication lists and care plans, checks for substitute items, verifies device-supply dependencies, and notifies care teams with a prioritized action plan.

**WF-07: Admission Supply Readiness** (4 steps | Patient Monitoring + Inventory Management + Device Management)
Before a patient arrives on the floor, verifies that all required medications, consumables, and device supplies are available. Checks device readiness in the assigned room and creates reorder requests for any gaps.

**WF-08: Floor Situational Awareness** (4 steps | Patient Monitoring + Device Management + Inventory Management + Patient Engagement)
Generates a comprehensive shift handoff briefing combining patient acuity with AgentCore Memory insights, device health and monitoring gaps, supply levels and stockout risks, and nurse workload distribution. Replaces manual shift-start rounds with a synthesized, prioritized action list.

**WF-09: Bed Exit Fall Risk Assessment** (5 steps | Device Management + Patient Monitoring + Patient Engagement)
When a smart bed detects a patient getting up, correlates real-time vitals, current medications (especially those causing dizziness or orthostatic hypotension), time of day, and fall history to assess risk before the patient falls.

**WF-10: Pressure Injury Prevention** (4 steps | Device Management + Patient Monitoring + Patient Engagement)
Monitors smart bed pressure sensors to detect when patients have not been repositioned. Escalates based on Braden score, pressure zone readings, and comorbidities. Checks if wound care supplies are available on the floor.

**WF-12: Alert Triage & Fatigue Management** (5 steps | Patient Monitoring + Patient Engagement)
Intercepts every alert before it reaches a nurse. Suppresses device noise and repeat threshold alerts, bundles related alerts, and escalates only critical findings. Reduces alert volume by 60-80% while ensuring critical alerts are never suppressed.

**WF-13: Nurse Workload Query** (2 steps | Patient Engagement + Patient Monitoring)
Enables charge nurses to query alert loads, view suppressed alerts, check team workload distribution, and identify overloaded nurses before burnout affects patient care.

**WF-14: Patient Admission with Memory** (4 steps | Patient Monitoring + Device Management + Inventory Management + Patient Engagement)
Initializes AgentCore Memory for the patient with their clinical baseline, verifies device availability in the assigned room, checks supply readiness for the patient's needs, and sets up the care team with communication preferences.

**WF-15: Patient Discharge with Memory Cleanup** (4 steps | Patient Monitoring + Patient Engagement + Inventory Management)
Assesses discharge readiness using the full AgentCore Memory timeline, reviews the discharge plan and follow-up appointments, verifies discharge supply kits are available, generates a discharge summary from memory, and clears the patient's memory from both DynamoDB and AgentCore Memory.

## Clinical Workflows — Single-Agent

**WF-06: Vital Sign Early Warning** (3 steps | Patient Monitoring)
Detects subtle vital sign trends that individually look normal but collectively indicate a patient heading toward a critical event. Catches slowly declining patients 30-60 minutes before traditional threshold alerts would fire.

**WF-07: Predictive Maintenance** (4 steps | Device Management)
Predicts which devices are likely to fail in the coming 7/14/30 days based on telemetry trends. Prioritizes maintenance by patient dependency so the most clinically critical devices are serviced first.

**WF-08: Appointment No-Show Prediction** (4 steps | Patient Engagement)
Evaluates upcoming appointments for no-show risk based on adherence patterns, communication history, and patient engagement profile. Triggers proactive outreach for high-risk patients.

## MedTech Workflows — Device Manufacturer

**WF-09: Proactive Service Dispatch** (5 steps | Field Service + Inventory Management + Account Intelligence)
Scans the installed base across all hospital customers for devices predicted to need service. Checks parts availability at each site, creates an optimized FSE dispatch plan grouping nearby sites, and flags accounts with upcoming contract renewals where service quality matters most.

**WF-10: Post-Market Surveillance** (4 steps | Field Service + Account Intelligence)
Aggregates fleet-wide performance data for a specific device model across all hospitals. Compares firmware versions to detect quality signals, reviews service history for recurring failure patterns, and assesses which customer accounts are most affected.

**WF-11: Account Health Review** (4 steps | Account Intelligence + Field Service)
Calculates composite health scores for all hospital accounts based on device utilization, service trends, firmware compliance, and contract status. Identifies at-risk customers, reviews their service history, and generates a prioritized action plan for the commercial team.

**WF-16: Regulatory Recall Response** (5 steps | Field Service + Inventory Management + Account Intelligence)
When a safety recall is issued, instantly identifies every affected device across all hospital customers. Assesses risk severity per device, checks replacement parts availability at each site, creates a prioritized FSE dispatch plan, and evaluates the customer relationship impact to recommend proactive communication strategies.

**WF-17: Contract Renewal Package** (4 steps | Account Intelligence + Field Service)
Auto-generates a data-driven renewal package for a hospital account approaching contract expiry. Includes fleet health summary, quantified service value delivered, firmware upgrade benefits, and a risk assessment of what the hospital would lose without the contract.

**WF-18: Competitive Intelligence** (4 steps | Field Service + Account Intelligence)
Detects early signals that hospitals may be evaluating competitor devices by analyzing declining utilization, deferred firmware updates, dropping consumable orders, and service friction. Generates a competitive response strategy per account with specific actions for the sales team.
