"""WF-12: Patient Admission with Memory Initialization"""

WF12_PATIENT_ADMISSION = {
    "id": "WF-14",
    "name": "Patient Admission with Memory Initialization",
    "description": "Initializes patient memory profile, verifies device availability, checks supply readiness, and sets up care team for a new admission.",
    "steps": [
        {
            "step": 1,
            "agent": "patient-monitoring",
            "description": "Initialize patient memory and pull clinical profile",
            "prompt_template": "Initialize patient memory for {patient_id} being admitted to {room}. Pull their full clinical profile including conditions, medications, risk factors, and Braden score.",
        },
        {
            "step": 2,
            "agent": "device-management",
            "description": "Verify device availability in the assigned room",
            "prompt_template": "Patient {patient_id} is being admitted to {room}. Check what devices are available in that room — monitors, infusion pumps, smart beds. Are they all active and in good condition?",
        },
        {
            "step": 3,
            "agent": "inventory-management",
            "description": "Verify supply readiness for patient needs",
            "prompt_template": "Patient {patient_id} is being admitted with these needs: {step_1_response}. Check if the required medications and supplies are available on the floor. Flag any shortages.",
        },
        {
            "step": 4,
            "agent": "patient-engagement",
            "description": "Set up care team and communication preferences",
            "prompt_template": "Patient {patient_id} has been admitted to {room}. Set up the care team assignment and review communication preferences. Patient profile: {step_1_response}.",
        },
    ],
}
