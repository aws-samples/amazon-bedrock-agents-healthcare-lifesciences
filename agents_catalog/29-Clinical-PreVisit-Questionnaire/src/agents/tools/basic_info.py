from strands import tool
from ...utils.validators import validate_phone, validate_date
import datetime

class BasicInfoTools:
    def __init__(self, pvq_data):
        self.pvq_data = pvq_data
    
    @tool
    def save_basic_info(self, field: str, value: str) -> str:
        """Save basic patient information"""
        fields = {'name': 'patient_name', 'address': 'home_address', 'phone': 'phone', 'dob': 'date_of_birth', 'sex': 'sex'}
        
        field_key = field.lower()
        if field_key not in fields:
            return f"❌ Unknown field: {field}"
        
        if field_key == 'phone' and not validate_phone(value):
            return f"❌ Invalid phone format"
        if field_key == 'dob' and not validate_date(value):
            return f"❌ Invalid date format"
        
        setattr(self.pvq_data, fields[field_key], value)
        if field_key == 'name':
            self.pvq_data.date_completed = datetime.datetime.now().strftime("%m/%d/%Y")
        
        return f"✅ Saved {field}: {value}"