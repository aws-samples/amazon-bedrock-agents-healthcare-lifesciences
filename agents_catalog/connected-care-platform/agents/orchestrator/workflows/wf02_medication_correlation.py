"""WF-02: Medication-Device-Vitals Correlation"""

WF02_MEDICATION_CORRELATION = {
    "id": "WF-02",
    "name": "Medication-Device-Vitals Correlation",
    "description": "Investigates whether a vital sign anomaly is caused by medication changes, device malfunction, or a clinical event.",
    "steps": [
        {
            "step": 1,
            "agent": "patient-monitoring",
            "description": "Characterize the vital sign anomaly",
            "prompt_template": "Patient {patient_id} has an anomalous vital sign reading. Characterize the anomaly: what vital sign is affected, how far from baseline, when did it start, and what is the trend?",
        },
        {
            "step": 2,
            "agent": "patient-engagement",
            "description": "Check recent medication changes and administration",
            "prompt_template": "Check the medication history for patient {patient_id} over the last 72 hours. List any new medications started, dose changes, and administration times. Include known side effects of current medications.",
        },
        {
            "step": 3,
            "agent": "device-management",
            "description": "Verify medication delivery device accuracy",
            "prompt_template": "Check all devices assigned to or near patient {patient_id}. Verify device accuracy, check for any error events, and report if any infusion pumps or medication dispensers show anomalies.",
        },
        {
            "step": 4,
            "agent": "patient-monitoring",
            "description": "Correlate findings and determine probable cause",
            "prompt_template": "Based on the following findings, determine the probable cause of the vital sign anomaly for patient {patient_id}. Medication findings: {step_2_response}. Device findings: {step_3_response}. Is this a medication side effect, device error, or independent clinical event?",
        },
        {
            "step": 5,
            "agent": "patient-engagement",
            "description": "Notify prescribing physician with correlation report",
            "prompt_template": "Send a notification to the prescribing physician for patient {patient_id} with the following correlation report: {step_4_response}. Flag for medication review if the anomaly is medication-related.",
        },
    ],
}
