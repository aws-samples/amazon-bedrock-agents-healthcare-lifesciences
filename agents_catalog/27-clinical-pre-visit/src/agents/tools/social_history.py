from strands import tool

class SocialHistoryTools:
    def __init__(self, pvq_data):
        self.pvq_data = pvq_data
    
    @tool
    def save_social_history(self, field: str, value: str) -> str:
        fields = {'living': 'living_with', 'residence': 'residence_type', 'marital': 'marital_status', 'education': 'education_level'}
        
        field_key = next((k for k in fields if k in field.lower()), None)
        if not field_key:
            return f"❌ Unknown field: {field}"
        
        attr_name = fields[field_key]
        if field_key == 'living':
            getattr(self.pvq_data, attr_name).append(value)
        else:
            setattr(self.pvq_data, attr_name, value)
        return f"✅ Saved {field}: {value}"
    
    @tool
    def save_family_history(self, condition: str, relative: str = "") -> str:
        entry = f"{condition} ({relative})" if relative else condition
        self.pvq_data.family_history.append(entry)
        return f"✅ Added family history: {condition}"