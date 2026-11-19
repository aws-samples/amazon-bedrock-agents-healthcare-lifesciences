from strands import tool
import json
import datetime

class UtilityTools:
    def __init__(self, pvq_data, medical_categories):
        self.pvq_data = pvq_data
        self.medical_categories = medical_categories
    
    @tool
    def get_progress(self) -> str:
        status = self.pvq_data.get_completion_status()
        items = [
            f"Basic: {'✅' if status['basic_info'] else '❌'}",
            f"Medical: {'✅' if status['has_medical_history'] else '❌'}",
            f"Meds: {len(self.pvq_data.current_medications)}",
            f"Allergies: {len(self.pvq_data.drug_allergies)}",
            f"Symptoms: {len(self.pvq_data.recent_symptoms)}"
        ]
        return "📋 Progress:\n" + "\n".join(items)
    
    @tool
    def get_medical_categories(self) -> str:
        categories = self.medical_categories.get_category_mapping()
        result = "🏥 Categories:\n"
        for cat, conditions in list(categories.items())[:5]:
            result += f"{cat}: {conditions[0]}...\n"
        return result
    
    @tool
    def save_to_file(self, filename: str = "") -> str:
        if not filename:
            name = self.pvq_data.patient_name.replace(" ", "_") if self.pvq_data.patient_name else "patient"
            filename = f"pvq_{name}_{datetime.datetime.now().strftime('%Y%m%d')}.json"
        
        data = self.pvq_data.to_dict()
        data['timestamp'] = datetime.datetime.now().isoformat()
        
        try:
            with open(f"data/{filename}", 'w') as f:
                json.dump(data, f, indent=2)
            return f"💾 Saved to data/{filename}"
        except Exception as e:
            return f"❌ Save failed: {str(e)}"