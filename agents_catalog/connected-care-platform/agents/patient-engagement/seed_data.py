"""Comprehensive engagement seed data for 5 existing patients."""

ENGAGEMENT_PROFILES = [
    {
        "patient_id": "P-10001",
        "name": "Margaret Chen",
        "communication_preferences": {
            "preferred_channel": "phone",
            "language": "English",
            "contact_times": "9am-5pm",
            "sms_enabled": True,
            "email": "m.chen@example.com",
            "phone": "555-0101",
        },
        "care_team": [
            {"role": "Primary Physician", "name": "Dr. Sarah Williams", "id": "CT-001"},
            {"role": "Cardiologist", "name": "Dr. James Park", "id": "CT-002"},
            {"role": "Primary Nurse", "name": "RN Maria Santos", "id": "CT-003"},
            {"role": "Endocrinologist", "name": "Dr. Priya Sharma", "id": "CT-004"},
        ],
        "family_caregivers": [
            {"name": "David Chen", "relationship": "Son", "phone": "555-0102", "email": "d.chen@example.com", "access_level": "full"},
        ],
        "discharge_plan": {
            "discharge_date": "2026-03-20",
            "conditions_to_monitor": ["CHF exacerbation", "Blood glucose control", "Kidney function"],
            "follow_up_appointments": [
                {"type": "Cardiology follow-up", "days_post_discharge": 7},
                {"type": "Endocrinology check", "days_post_discharge": 14},
                {"type": "Primary care", "days_post_discharge": 30},
            ],
            "activity_restrictions": "No heavy lifting for 2 weeks",
        },
        "health_education": [
            {"topic": "CHF Self-Management", "delivered": "2026-03-19", "completed": True},
            {"topic": "Diabetic Diet Guidelines", "delivered": "2026-03-18", "completed": True},
            {"topic": "Medication Management", "delivered": "2026-03-20", "completed": False},
        ],
        "telehealth_history": [
            {"date": "2026-03-10", "provider": "Dr. Sarah Williams", "type": "Follow-up", "outcome": "Medication adjusted"},
        ],
    },
    {
        "patient_id": "P-10002",
        "name": "James Rodriguez",
        "communication_preferences": {
            "preferred_channel": "sms",
            "language": "English",
            "contact_times": "8am-8pm",
            "sms_enabled": True,
            "email": "j.rodriguez@example.com",
            "phone": "555-0201",
        },
        "care_team": [
            {"role": "Cardiac Surgeon", "name": "Dr. Michael Torres", "id": "CT-005"},
            {"role": "Primary Nurse", "name": "RN Lisa Chang", "id": "CT-006"},
            {"role": "Physical Therapist", "name": "PT John Adams", "id": "CT-007"},
        ],
        "family_caregivers": [
            {"name": "Elena Rodriguez", "relationship": "Wife", "phone": "555-0202", "email": "e.rodriguez@example.com", "access_level": "full"},
        ],
        "discharge_plan": None,
        "health_education": [
            {"topic": "Post-CABG Recovery", "delivered": "2026-03-22", "completed": True},
            {"topic": "Cardiac Rehabilitation", "delivered": "2026-03-23", "completed": False},
        ],
        "telehealth_history": [],
    },
    {
        "patient_id": "P-10003",
        "name": "Aisha Patel",
        "communication_preferences": {
            "preferred_channel": "email",
            "language": "English",
            "contact_times": "10am-6pm",
            "sms_enabled": True,
            "email": "a.patel@example.com",
            "phone": "555-0301",
        },
        "care_team": [
            {"role": "Primary Physician", "name": "Dr. Robert Kim", "id": "CT-008"},
            {"role": "Endocrinologist", "name": "Dr. Priya Sharma", "id": "CT-004"},
            {"role": "Pulmonologist", "name": "Dr. Angela Foster", "id": "CT-009"},
        ],
        "family_caregivers": [
            {"name": "Raj Patel", "relationship": "Husband", "phone": "555-0302", "email": "r.patel@example.com", "access_level": "full"},
            {"name": "Meera Patel", "relationship": "Daughter", "phone": "555-0303", "email": "meera.p@example.com", "access_level": "read-only"},
        ],
        "discharge_plan": None,
        "health_education": [
            {"topic": "Insulin Management", "delivered": "2026-03-15", "completed": True},
            {"topic": "Asthma Action Plan", "delivered": "2026-03-16", "completed": True},
        ],
        "telehealth_history": [
            {"date": "2026-03-05", "provider": "Dr. Priya Sharma", "type": "Diabetes review", "outcome": "Insulin dose adjusted"},
            {"date": "2026-02-20", "provider": "Dr. Angela Foster", "type": "Asthma check", "outcome": "Stable, continue current regimen"},
        ],
    },
    {
        "patient_id": "P-10004",
        "name": "Robert Kim",
        "communication_preferences": {
            "preferred_channel": "app",
            "language": "English",
            "contact_times": "anytime",
            "sms_enabled": True,
            "email": "r.kim@example.com",
            "phone": "555-0401",
        },
        "care_team": [
            {"role": "Surgeon", "name": "Dr. Helen Park", "id": "CT-010"},
            {"role": "Primary Nurse", "name": "RN David Brown", "id": "CT-011"},
        ],
        "family_caregivers": [
            {"name": "Susan Kim", "relationship": "Wife", "phone": "555-0402", "email": "s.kim@example.com", "access_level": "full"},
        ],
        "discharge_plan": {
            "discharge_date": "2026-03-26",
            "conditions_to_monitor": ["Surgical site infection", "Pain management"],
            "follow_up_appointments": [
                {"type": "Surgical follow-up", "days_post_discharge": 7},
                {"type": "Primary care", "days_post_discharge": 14},
            ],
            "activity_restrictions": "No strenuous activity for 4 weeks",
        },
        "health_education": [
            {"topic": "Post-Appendectomy Care", "delivered": "2026-03-24", "completed": True},
        ],
        "telehealth_history": [],
    },
    {
        "patient_id": "P-10005",
        "name": "Linda Okafor",
        "communication_preferences": {
            "preferred_channel": "sms",
            "language": "English",
            "contact_times": "9am-9pm",
            "sms_enabled": True,
            "email": "l.okafor@example.com",
            "phone": "555-0501",
        },
        "care_team": [
            {"role": "Primary Physician", "name": "Dr. Thomas Lee", "id": "CT-012"},
            {"role": "Primary Nurse", "name": "RN Jennifer White", "id": "CT-013"},
        ],
        "family_caregivers": [
            {"name": "Emmanuel Okafor", "relationship": "Father", "phone": "555-0502", "email": "e.okafor@example.com", "access_level": "read-only"},
        ],
        "discharge_plan": {
            "discharge_date": "2026-03-27",
            "conditions_to_monitor": ["Pneumonia resolution", "Fever monitoring"],
            "follow_up_appointments": [
                {"type": "Pulmonology follow-up", "days_post_discharge": 10},
            ],
            "activity_restrictions": "Rest, avoid cold environments",
        },
        "health_education": [
            {"topic": "Pneumonia Recovery", "delivered": "2026-03-24", "completed": False},
        ],
        "telehealth_history": [
            {"date": "2026-03-22", "provider": "Dr. Thomas Lee", "type": "Initial assessment", "outcome": "Admitted for observation"},
        ],
    },
]

MEDICATIONS = [
    # P-10001 — Margaret Chen (critical, CHF + Diabetes + CKD)
    {"patient_id": "P-10001", "medication_id": "MED-001", "name": "Lisinopril", "dose": "20mg", "frequency": "daily", "prescriber": "Dr. Sarah Williams",
     "start_date": "2025-06-01", "side_effects": ["Dizziness", "Dry cough", "Hyperkalemia"], "refill_due": "2026-04-01", "refills_remaining": 3,
     "change_history": [{"date": "2026-01-15", "change": "Dose increased from 10mg to 20mg", "reason": "BP not adequately controlled"}]},
    {"patient_id": "P-10001", "medication_id": "MED-002", "name": "Metformin", "dose": "1000mg", "frequency": "twice daily", "prescriber": "Dr. Priya Sharma",
     "start_date": "2024-03-10", "side_effects": ["Nausea", "Diarrhea", "Lactic acidosis (rare)"], "refill_due": "2026-04-05", "refills_remaining": 5,
     "change_history": []},
    {"patient_id": "P-10001", "medication_id": "MED-003", "name": "Furosemide", "dose": "40mg", "frequency": "daily", "prescriber": "Dr. James Park",
     "start_date": "2025-09-20", "side_effects": ["Dehydration", "Electrolyte imbalance", "Dizziness"], "refill_due": "2026-03-28", "refills_remaining": 2,
     "change_history": [{"date": "2026-03-01", "change": "Added to regimen", "reason": "Fluid retention from CHF"}]},
    {"patient_id": "P-10001", "medication_id": "MED-004", "name": "Metoprolol", "dose": "50mg", "frequency": "twice daily", "prescriber": "Dr. James Park",
     "start_date": "2025-01-15", "side_effects": ["Fatigue", "Bradycardia", "Cold extremities"], "refill_due": "2026-04-10", "refills_remaining": 4,
     "change_history": []},
    # P-10002 — James Rodriguez (moderate, post-CABG)
    {"patient_id": "P-10002", "medication_id": "MED-005", "name": "Amlodipine", "dose": "10mg", "frequency": "daily", "prescriber": "Dr. Michael Torres",
     "start_date": "2024-11-01", "side_effects": ["Edema", "Dizziness", "Flushing"], "refill_due": "2026-04-15", "refills_remaining": 6,
     "change_history": []},
    {"patient_id": "P-10002", "medication_id": "MED-006", "name": "Aspirin", "dose": "81mg", "frequency": "daily", "prescriber": "Dr. Michael Torres",
     "start_date": "2026-03-18", "side_effects": ["GI bleeding", "Bruising"], "refill_due": "2026-05-01", "refills_remaining": 11,
     "change_history": [{"date": "2026-03-18", "change": "Started post-CABG", "reason": "Antiplatelet therapy after surgery"}]},
    {"patient_id": "P-10002", "medication_id": "MED-007", "name": "Atorvastatin", "dose": "40mg", "frequency": "daily", "prescriber": "Dr. Michael Torres",
     "start_date": "2024-11-01", "side_effects": ["Muscle pain", "Liver enzyme elevation"], "refill_due": "2026-04-20", "refills_remaining": 5,
     "change_history": []},
    # P-10003 — Aisha Patel (moderate, T1D + Asthma)
    {"patient_id": "P-10003", "medication_id": "MED-008", "name": "Insulin Glargine", "dose": "24 units", "frequency": "daily", "prescriber": "Dr. Priya Sharma",
     "start_date": "2023-01-10", "side_effects": ["Hypoglycemia", "Weight gain", "Injection site reactions"], "refill_due": "2026-04-01", "refills_remaining": 4,
     "change_history": [{"date": "2026-03-05", "change": "Dose increased from 20 to 24 units", "reason": "A1C above target"}]},
    {"patient_id": "P-10003", "medication_id": "MED-009", "name": "Fluticasone/Salmeterol", "dose": "250/50mcg", "frequency": "twice daily", "prescriber": "Dr. Angela Foster",
     "start_date": "2024-06-15", "side_effects": ["Oral thrush", "Hoarseness", "Tremor"], "refill_due": "2026-04-10", "refills_remaining": 3,
     "change_history": []},
    # P-10004 — Robert Kim (stable, post-appendectomy)
    {"patient_id": "P-10004", "medication_id": "MED-010", "name": "Acetaminophen", "dose": "500mg", "frequency": "every 6 hours", "prescriber": "Dr. Helen Park",
     "start_date": "2026-03-23", "side_effects": ["Liver toxicity (overdose)"], "refill_due": "2026-04-23", "refills_remaining": 1,
     "change_history": [{"date": "2026-03-23", "change": "Started post-surgery", "reason": "Pain management"}]},
    # P-10005 — Linda Okafor (stable, pneumonia)
    {"patient_id": "P-10005", "medication_id": "MED-011", "name": "Azithromycin", "dose": "500mg", "frequency": "daily", "prescriber": "Dr. Thomas Lee",
     "start_date": "2026-03-22", "side_effects": ["Nausea", "Diarrhea", "QT prolongation (rare)"], "refill_due": "2026-03-27", "refills_remaining": 0,
     "change_history": [{"date": "2026-03-22", "change": "Started for pneumonia", "reason": "Community-acquired pneumonia treatment"}]},
    {"patient_id": "P-10005", "medication_id": "MED-012", "name": "Ibuprofen", "dose": "400mg", "frequency": "every 8 hours", "prescriber": "Dr. Thomas Lee",
     "start_date": "2026-03-22", "side_effects": ["GI upset", "Kidney impairment", "Bleeding risk"], "refill_due": "2026-04-22", "refills_remaining": 2,
     "change_history": []},
]

APPOINTMENTS = [
    # P-10001 — Margaret Chen
    {"patient_id": "P-10001", "appointment_id": "APT-001", "type": "Cardiology follow-up", "provider": "Dr. James Park", "date": "2026-03-27", "time": "10:00", "location": "Cardiology Clinic B", "status": "scheduled"},
    {"patient_id": "P-10001", "appointment_id": "APT-002", "type": "Endocrinology check", "provider": "Dr. Priya Sharma", "date": "2026-04-03", "time": "14:00", "location": "Diabetes Center", "status": "scheduled"},
    {"patient_id": "P-10001", "appointment_id": "APT-H01", "type": "Primary care", "provider": "Dr. Sarah Williams", "date": "2026-03-10", "time": "09:00", "location": "Primary Care Office", "status": "attended"},
    {"patient_id": "P-10001", "appointment_id": "APT-H02", "type": "Cardiology", "provider": "Dr. James Park", "date": "2026-02-15", "time": "11:00", "location": "Cardiology Clinic B", "status": "attended"},
    {"patient_id": "P-10001", "appointment_id": "APT-H03", "type": "Lab work", "provider": "Lab Services", "date": "2026-01-20", "time": "08:00", "location": "Lab Building A", "status": "missed"},
    # P-10002 — James Rodriguez
    {"patient_id": "P-10002", "appointment_id": "APT-003", "type": "Surgical follow-up", "provider": "Dr. Michael Torres", "date": "2026-03-28", "time": "09:00", "location": "Surgery Clinic", "status": "scheduled"},
    {"patient_id": "P-10002", "appointment_id": "APT-004", "type": "Cardiac rehab", "provider": "PT John Adams", "date": "2026-04-01", "time": "13:00", "location": "Rehab Center", "status": "scheduled"},
    {"patient_id": "P-10002", "appointment_id": "APT-H04", "type": "Pre-op assessment", "provider": "Dr. Michael Torres", "date": "2026-03-15", "time": "10:00", "location": "Surgery Clinic", "status": "attended"},
    # P-10003 — Aisha Patel
    {"patient_id": "P-10003", "appointment_id": "APT-005", "type": "Diabetes review", "provider": "Dr. Priya Sharma", "date": "2026-04-05", "time": "11:00", "location": "Diabetes Center", "status": "scheduled"},
    {"patient_id": "P-10003", "appointment_id": "APT-H05", "type": "Pulmonology", "provider": "Dr. Angela Foster", "date": "2026-03-01", "time": "14:00", "location": "Pulmonology Clinic", "status": "attended"},
    {"patient_id": "P-10003", "appointment_id": "APT-H06", "type": "Diabetes review", "provider": "Dr. Priya Sharma", "date": "2026-02-10", "time": "10:00", "location": "Diabetes Center", "status": "cancelled"},
    {"patient_id": "P-10003", "appointment_id": "APT-H07", "type": "Primary care", "provider": "Dr. Robert Kim", "date": "2026-01-15", "time": "09:00", "location": "Primary Care Office", "status": "missed"},
    # P-10004 — Robert Kim
    {"patient_id": "P-10004", "appointment_id": "APT-006", "type": "Surgical follow-up", "provider": "Dr. Helen Park", "date": "2026-03-30", "time": "10:00", "location": "Surgery Clinic", "status": "scheduled"},
    {"patient_id": "P-10004", "appointment_id": "APT-H08", "type": "Emergency admission", "provider": "ER", "date": "2026-03-23", "time": "02:00", "location": "Emergency Dept", "status": "attended"},
    # P-10005 — Linda Okafor
    {"patient_id": "P-10005", "appointment_id": "APT-007", "type": "Pulmonology follow-up", "provider": "Dr. Thomas Lee", "date": "2026-04-06", "time": "15:00", "location": "Pulmonology Clinic", "status": "scheduled"},
    {"patient_id": "P-10005", "appointment_id": "APT-H09", "type": "Urgent care", "provider": "Dr. Thomas Lee", "date": "2026-03-22", "time": "10:00", "location": "Urgent Care", "status": "attended"},
]

MEDICATION_ADHERENCE = [
    # P-10001 — mostly adherent but misses some doses
    {"patient_id": "P-10001", "record_id": "ADH-001", "medication_id": "MED-001", "date": "2026-03-24", "time": "08:00", "status": "taken"},
    {"patient_id": "P-10001", "record_id": "ADH-002", "medication_id": "MED-002", "date": "2026-03-24", "time": "08:15", "status": "taken"},
    {"patient_id": "P-10001", "record_id": "ADH-003", "medication_id": "MED-002", "date": "2026-03-24", "time": "20:00", "status": "missed"},
    {"patient_id": "P-10001", "record_id": "ADH-004", "medication_id": "MED-003", "date": "2026-03-24", "time": "09:00", "status": "taken"},
    {"patient_id": "P-10001", "record_id": "ADH-005", "medication_id": "MED-004", "date": "2026-03-24", "time": "08:00", "status": "taken"},
    {"patient_id": "P-10001", "record_id": "ADH-006", "medication_id": "MED-004", "date": "2026-03-24", "time": "20:00", "status": "late"},
    # P-10003 — poor adherence (diabetes concern)
    {"patient_id": "P-10003", "record_id": "ADH-007", "medication_id": "MED-008", "date": "2026-03-24", "time": "22:00", "status": "taken"},
    {"patient_id": "P-10003", "record_id": "ADH-008", "medication_id": "MED-009", "date": "2026-03-24", "time": "08:00", "status": "missed"},
    {"patient_id": "P-10003", "record_id": "ADH-009", "medication_id": "MED-009", "date": "2026-03-24", "time": "20:00", "status": "missed"},
    {"patient_id": "P-10003", "record_id": "ADH-010", "medication_id": "MED-008", "date": "2026-03-23", "time": "22:00", "status": "missed"},
    # P-10005 — good adherence
    {"patient_id": "P-10005", "record_id": "ADH-011", "medication_id": "MED-011", "date": "2026-03-24", "time": "09:00", "status": "taken"},
    {"patient_id": "P-10005", "record_id": "ADH-012", "medication_id": "MED-012", "date": "2026-03-24", "time": "08:00", "status": "taken"},
    {"patient_id": "P-10005", "record_id": "ADH-013", "medication_id": "MED-012", "date": "2026-03-24", "time": "16:00", "status": "taken"},
]

COMMUNICATION_LOG = [
    {"patient_id": "P-10001", "log_id": "LOG-001", "timestamp": "2026-03-24T09:00:00Z", "channel": "phone", "type": "appointment_reminder", "content": "Reminder: Cardiology follow-up with Dr. Park on March 27 at 10:00 AM", "status": "delivered"},
    {"patient_id": "P-10001", "log_id": "LOG-002", "timestamp": "2026-03-23T14:00:00Z", "channel": "sms", "type": "medication_reminder", "content": "Time for your evening Metformin dose", "status": "delivered"},
    {"patient_id": "P-10003", "log_id": "LOG-003", "timestamp": "2026-03-24T08:00:00Z", "channel": "email", "type": "medication_reminder", "content": "Reminder: Take your morning Fluticasone/Salmeterol", "status": "delivered"},
    {"patient_id": "P-10003", "log_id": "LOG-004", "timestamp": "2026-03-23T20:00:00Z", "channel": "email", "type": "adherence_alert", "content": "You missed your insulin dose today. Please take it as soon as possible.", "status": "delivered"},
    {"patient_id": "P-10005", "log_id": "LOG-005", "timestamp": "2026-03-24T09:00:00Z", "channel": "sms", "type": "medication_reminder", "content": "Time for your Azithromycin dose", "status": "delivered"},
]
