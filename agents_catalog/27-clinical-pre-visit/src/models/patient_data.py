"""
Patient data models for UCLA Health Pre-Visit Questionnaire
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import datetime

@dataclass
class PVQData:
    """Patient data structure matching PDF form fields"""
    # Basic Information
    date_completed: str = ""
    patient_name: str = ""
    home_address: str = ""
    phone: str = ""
    date_of_birth: str = ""
    sex: str = ""
    
    # Form completion info
    completed_by: str = ""  # Self or Other
    form_helper: Dict[str, str] = None  # Name, phone, relationship
    
    # Primary Care Doctor
    primary_care_doctor: Dict[str, str] = None  # Name, address, phone, fax
    continue_with_pcp: str = ""  # Yes/No/Not sure
    
    # Medical History Categories
    eye_ear_conditions: List[str] = None
    lung_conditions: List[str] = None
    heart_conditions: List[str] = None
    kidney_urinary_conditions: List[str] = None
    bone_joint_conditions: List[str] = None
    gastrointestinal_conditions: List[str] = None
    gland_conditions: List[str] = None
    nervous_system_conditions: List[str] = None
    other_health_problems: List[str] = None
    
    # Surgeries
    surgeries: List[Dict[str, str]] = None  # Surgery name and date
    
    # Hospitalizations (last 5 years)
    hospitalizations: List[Dict[str, str]] = None  # Reason and year
    
    # Medications & Allergies
    current_medications: List[Dict[str, str]] = None
    drug_allergies: List[Dict[str, str]] = None
    
    # Social History
    living_with: List[str] = None
    residence_type: str = ""
    facility_contact: Dict[str, str] = None  # For assisted living
    marital_status: str = ""
    children_count: str = ""
    children_contact: str = ""  # Yes/No
    education_level: str = ""
    employment_status: str = ""
    occupations: List[str] = None
    
    # Emergency contacts
    emergency_contacts: List[Dict[str, str]] = None
    permission_to_contact: str = ""  # Yes/No
    
    # Care assistance
    paid_helper: Dict[str, str] = None  # Hours, days, sufficient
    family_help: Dict[str, str] = None  # Hours, days, sufficient
    provides_care: str = ""  # Yes/No
    
    # Substance use
    alcohol_use: Dict[str, str] = None  # Frequency, amount, concerns
    smoking_history: Dict[str, str] = None  # Current, past, packs/day
    
    # Family History
    family_history: List[str] = None
    
    # Healthcare planning
    medical_power_attorney: str = ""  # Yes/No
    healthcare_proxy: Dict[str, str] = None  # Name, relationship, phone
    advance_directive: str = ""  # Yes/No
    
    # General outlook
    health_rating: str = ""  # Excellent/Good/Fair/Poor
    depression_screening: Dict[str, str] = None  # Interest, mood ratings
    
    # Mobility and falls
    walking_aids: List[str] = None
    afraid_falling: str = ""  # Yes/No
    fall_history: Dict[str, str] = None  # Details about recent falls
    
    # Health maintenance
    seatbelt_use: str = ""  # Yes/No
    exercise: Dict[str, str] = None  # Types, frequency
    vaccinations: Dict[str, str] = None  # Dates and reactions
    screening_tests: Dict[str, str] = None  # Various screening dates/results
    
    # Recent symptoms (last 3 months)
    recent_symptoms: List[str] = None
    
    # Health concerns
    health_concerns: List[str] = None
    
    # Referral info
    referral_source: List[str] = None
    zip_code: str = ""
    age: str = ""
    ucla_50plus_member: str = ""  # Yes/No
    
    def __post_init__(self):
        """Initialize empty lists for None fields"""
        list_fields = [
            'eye_ear_conditions', 'lung_conditions', 'heart_conditions',
            'kidney_urinary_conditions', 'bone_joint_conditions', 'gastrointestinal_conditions',
            'gland_conditions', 'nervous_system_conditions', 'other_health_problems',
            'surgeries', 'hospitalizations', 'current_medications', 'drug_allergies',
            'living_with', 'occupations', 'emergency_contacts', 'family_history',
            'walking_aids', 'recent_symptoms', 'health_concerns', 'referral_source'
        ]
        
        dict_fields = [
            'form_helper', 'primary_care_doctor', 'facility_contact', 'paid_helper',
            'family_help', 'alcohol_use', 'smoking_history', 'healthcare_proxy',
            'depression_screening', 'fall_history', 'exercise', 'vaccinations',
            'screening_tests'
        ]
        
        for field in dict_fields:
            if getattr(self, field) is None:
                setattr(self, field, {})
        
        for field in list_fields:
            if getattr(self, field) is None:
                setattr(self, field, [])
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def get_completion_status(self) -> Dict[str, bool]:
        """Check completion status of different sections"""
        return {
            'basic_info': all([
                self.patient_name, self.home_address, self.phone,
                self.date_of_birth, self.sex
            ]),
            'has_medical_history': any([
                self.eye_ear_conditions, self.lung_conditions, self.heart_conditions,
                self.kidney_urinary_conditions, self.bone_joint_conditions,
                self.gastrointestinal_conditions, self.gland_conditions,
                self.nervous_system_conditions, self.other_health_problems
            ]),
            'has_surgeries': bool(self.surgeries),
            'has_hospitalizations': bool(self.hospitalizations),
            'has_medications': bool(self.current_medications),
            'has_allergies': bool(self.drug_allergies),
            'has_social_history': any([
                self.living_with, self.marital_status, self.education_level
            ]),
            'has_family_history': bool(self.family_history),
            'has_recent_symptoms': bool(self.recent_symptoms),
            'has_health_concerns': bool(self.health_concerns)
        }

@dataclass
class MedicalConditionCategories:
    """Medical condition categories from the PDF form"""
    
    EYE_EAR = [
        "Macular degeneration", "Cataracts", "Glaucoma", 
        "Hearing loss/hearing aid"
    ]
    
    LUNGS = [
        "Asthma", "COPD/emphysema", "Bronchitis", "Recurrent pneumonias"
    ]
    
    HEART = [
        "Heart attack", "Heart failure", "High blood pressure",
        "Aortic stenosis", "Heart valve problem", "Angina",
        "High cholesterol", "Pacemaker", "Atrial fibrillation",
        "Irregular heartbeats"
    ]
    
    KIDNEY_URINARY = [
        "Frequent bladder infections", "Kidney disease", "Enlarged prostate",
        "Urinary incontinence", "Kidney stones"
    ]
    
    BONES_JOINTS = [
        "Gout", "Lower back pain", "Osteoporosis", "Arthritis (hip)",
        "Arthritis (knee)", "Arthritis (shoulder)", "Arthritis (back)",
        "Arthritis (hands)", "Fractured bone (hip)", "Fractured bone (spine)",
        "Fractured bone (wrist)"
    ]
    
    GASTROINTESTINAL = [
        "Heartburn/reflux/GERD", "Ulcers", "Irritable bowel",
        "Liver disease/cirrhosis", "Hepatitis", "Gallbladder disease",
        "Colon polyps", "Diverticulosis", "Bleeding problems",
        "Constipation", "Hemorrhoids"
    ]
    
    GLAND = [
        "Thyroid overactive (high)", "Thyroid underactive (low)", "Diabetes"
    ]
    
    NERVOUS_SYSTEM = [
        "Dementia or Alzheimer's disease", "Parkinson's disease", "Stroke",
        "Epilepsy or seizures", "Neuropathy/nerve damage", "Depression", "Anxiety"
    ]
    
    OTHER_HEALTH = [
        "Thrombosis/blood clots (leg)", "Thrombosis/blood clots (lung)",
        "Syncope (loss of consciousness)", "Hernia", "Anemia",
        "Sexual function problems", "Cancer (Breast)", "Cancer (Prostate)",
        "Cancer (Colon/Rectum)", "Cancer (Lung)", "Cancer (Skin)",
        "Cancer (Lymphatic)"
    ]
    
    @classmethod
    def get_category_mapping(cls) -> Dict[str, List[str]]:
        """Get mapping of category names to condition lists"""
        return {
            'eye_ear': cls.EYE_EAR,
            'lungs': cls.LUNGS,
            'heart': cls.HEART,
            'kidney_urinary': cls.KIDNEY_URINARY,
            'bones_joints': cls.BONES_JOINTS,
            'gastrointestinal': cls.GASTROINTESTINAL,
            'gland': cls.GLAND,
            'nervous_system': cls.NERVOUS_SYSTEM,
            'other_health': cls.OTHER_HEALTH
        }