from strands import tool

class HealthMaintenanceTools:
    def __init__(self, pvq_data):
        self.pvq_data = pvq_data
    
    @tool
    def save_healthcare_planning(self, field: str, value: str) -> str:
        fields = {'attorney': 'medical_power_attorney', 'directive': 'advance_directive', 'rating': 'health_rating'}
        
        field_key = next((k for k in fields if k in field.lower()), None)
        if field_key:
            setattr(self.pvq_data, fields[field_key], value)
            return f"✅ Saved {field}: {value}"
        return f"❌ Unknown field: {field}"
    
    @tool
    def save_health_maintenance(self, field: str, value: str) -> str:
        if 'seatbelt' in field.lower():
            self.pvq_data.seatbelt_use = value
        elif 'exercise' in field.lower():
            self.pvq_data.exercise[field.lower()] = value
        else:
            return f"❌ Unknown field: {field}"
        return f"✅ Saved {field}: {value}"