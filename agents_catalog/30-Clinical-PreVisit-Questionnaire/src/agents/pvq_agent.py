from strands import Agent
from ..models.patient_data import PVQData, MedicalConditionCategories
from .tools.basic_info import BasicInfoTools
from .tools.medical_history import MedicalHistoryTools
from .tools.medications import MedicationTools
from .tools.social_history import SocialHistoryTools
from .tools.health_maintenance import HealthMaintenanceTools
from .tools.symptoms import SymptomTools
from .tools.utilities import UtilityTools

class PVQStrandsAgent:
    def __init__(self):
        self.pvq_data = PVQData()
        self.medical_categories = MedicalConditionCategories()
        
        self.basic_info = BasicInfoTools(self.pvq_data)
        self.medical_history = MedicalHistoryTools(self.pvq_data)
        self.medications = MedicationTools(self.pvq_data)
        self.social_history = SocialHistoryTools(self.pvq_data)
        self.health_maintenance = HealthMaintenanceTools(self.pvq_data)
        self.symptoms = SymptomTools(self.pvq_data)
        self.utilities = UtilityTools(self.pvq_data, self.medical_categories)
        
        system_prompt = """You help patients complete UCLA Health Pre-Visit Questionnaire. 

Guidelines:
- Ask one question at a time
- Use available tools to save all information
- For medical conditions, use save_medical_condition or save_health_condition
- Be direct and helpful, avoid apologizing
- If a tool fails, try the general save_health_condition tool
- Guide patients through: basic info, medical history, medications, allergies, symptoms, social history, family history, health maintenance, utilities
- Use 'progress' to show current status, 'categories' for medical categories"""

        self.agent = Agent(
            model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            system_prompt=system_prompt,
            tools=[
                self.basic_info.save_basic_info,
                self.medical_history.save_medical_condition,
                self.medical_history.save_health_condition,
                self.medical_history.save_surgery,
                self.medical_history.save_hospitalization,
                self.medications.save_medication,
                self.medications.save_allergy,
                self.social_history.save_social_history,
                self.social_history.save_family_history,
                self.health_maintenance.save_healthcare_planning,
                self.health_maintenance.save_health_maintenance,
                self.symptoms.save_recent_symptom,
                self.symptoms.save_health_concern,
                self.utilities.get_progress,
                self.utilities.get_medical_categories,
                self.utilities.save_to_file
            ]
        )
    
    def chat(self, message: str) -> str:
        try:
            msg = message.lower()
            if msg in ['quit', 'exit', 'done']:
                self.utilities.save_to_file()
                return "👋 Saved. Thank you!"
            if msg in ['progress', 'status']:
                return self.utilities.get_progress()
            if msg in ['categories', 'conditions']:
                return self.utilities.get_medical_categories()
            
            result = self.agent(message)
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            return f"❌ Error: {str(e)}"