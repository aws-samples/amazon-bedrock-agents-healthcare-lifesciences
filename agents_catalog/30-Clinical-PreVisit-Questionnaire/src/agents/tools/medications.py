from strands import tool

class MedicationTools:
    def __init__(self, pvq_data):
        self.pvq_data = pvq_data
    
    @tool
    def save_medication(self, name: str, strength: str = "", frequency: str = "") -> str:
        self.pvq_data.current_medications.append({"name": name, "strength": strength, "frequency": frequency})
        return f"✅ Added medication: {name}"
    
    @tool
    def save_allergy(self, drug: str, reaction: str) -> str:
        self.pvq_data.drug_allergies.append({"drug": drug, "reaction": reaction})
        return f"⚠️ Added allergy: {drug}"