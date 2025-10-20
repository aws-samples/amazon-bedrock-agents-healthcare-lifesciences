from strands import tool

class SymptomTools:
    def __init__(self, pvq_data):
        self.pvq_data = pvq_data
    
    @tool
    def save_recent_symptom(self, symptom: str) -> str:
        self.pvq_data.recent_symptoms.append(symptom)
        return f"✅ Added symptom: {symptom}"
    
    @tool
    def save_health_concern(self, concern: str) -> str:
        self.pvq_data.health_concerns.append(concern)
        return f"✅ Added concern: {concern}"