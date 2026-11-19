from strands import tool

class MedicalHistoryTools:
    def __init__(self, pvq_data):
        self.pvq_data = pvq_data
    
    @tool
    def save_medical_condition(self, category: str, condition: str, year: str = "") -> str:
        """Save medical condition by category"""
        # Map common terms to field names
        category_lower = category.lower()
        
        # Use exact word matching to avoid substring issues (e.g., "ear" in "heart")
        import re
        
        def matches_category(category_text, terms):
            """Check if category matches any of the terms using word boundaries"""
            pattern = r'\b(' + '|'.join(terms) + r')\b'
            return bool(re.search(pattern, category_text, re.IGNORECASE))
        
        if matches_category(category_lower, ['eye', 'ear', 'vision', 'hearing']):
            field_name = 'eye_ear_conditions'
        elif matches_category(category_lower, ['lung', 'respiratory', 'breathing', 'asthma', 'copd']):
            field_name = 'lung_conditions'
        elif matches_category(category_lower, ['heart', 'cardiac', 'blood pressure', 'cholesterol']):
            field_name = 'heart_conditions'
        elif matches_category(category_lower, ['kidney', 'urinary', 'bladder']):
            field_name = 'kidney_urinary_conditions'
        elif matches_category(category_lower, ['bone', 'joint', 'arthritis', 'osteoporosis']):
            field_name = 'bone_joint_conditions'
        elif matches_category(category_lower, ['stomach', 'digestive', 'gi', 'gastrointestinal']):
            field_name = 'gastrointestinal_conditions'
        elif matches_category(category_lower, ['thyroid', 'diabetes', 'gland']):
            field_name = 'gland_conditions'
        elif matches_category(category_lower, ['brain', 'nervous', 'mental', 'depression', 'anxiety']):
            field_name = 'nervous_system_conditions'
        else:
            field_name = 'other_health_problems'
        
        entry = f"{condition} ({year})" if year else condition
        getattr(self.pvq_data, field_name).append(entry)
        return f"✅ Added {condition} to {category} conditions"
    
    @tool
    def save_surgery(self, surgery_name: str, date: str = "") -> str:
        self.pvq_data.surgeries.append({"name": surgery_name, "date": date})
        return f"✅ Added surgery: {surgery_name}"
    
    @tool
    def save_hospitalization(self, reason: str, year: str) -> str:
        self.pvq_data.hospitalizations.append({"reason": reason, "year": year})
        return f"✅ Added hospitalization: {reason}"
    
    @tool
    def save_health_condition(self, condition: str, year: str = "") -> str:
        """Save any health condition (fallback tool)"""
        entry = f"{condition} ({year})" if year else condition
        self.pvq_data.other_health_problems.append(entry)
        return f"✅ Added health condition: {condition}"