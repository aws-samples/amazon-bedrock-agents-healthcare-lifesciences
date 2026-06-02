"""
Validation utilities for patient data
"""

import re
import datetime

def validate_phone(phone: str):
    """Validate phone number format"""
    if not phone:
        return False
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Check for 10 digits or 11 digits with country code
    if len(digits) == 10:
        return True
    elif len(digits) == 11 and digits[0] == '1':
        return True
    
    return False

def format_phone(phone: str) -> str:
    """Format phone number to (XXX) XXX-XXXX"""
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    
    return phone

def validate_date(date_str: str):
    """Validate date format MM/DD/YYYY"""
    if not date_str:
        return False
    
    try:
        # Try to parse the date
        parsed_date = datetime.datetime.strptime(date_str, "%m/%d/%Y")
        
        # Check if date is reasonable
        current_year = datetime.datetime.now().year
        birth_year = parsed_date.year
        
        # Not in future, not more than 120 years ago
        if birth_year > current_year or current_year - birth_year > 120:
            return False
        
        return True
        
    except ValueError:
        return False

def validate_sex(sex: str):
    """Validate sex field"""
    if not sex:
        return False
    
    valid_values = ['male', 'm', 'female', 'f', 'other']
    return sex.lower() in valid_values

def normalize_sex(sex: str) -> str:
    """Normalize sex field to standard format"""
    if not sex:
        return ""
    
    sex_lower = sex.lower()
    if sex_lower in ['male', 'm']:
        return 'Male'
    elif sex_lower in ['female', 'f']:
        return 'Female'
    else:
        return sex.title()

def validate_required_fields(data: dict) -> list:
    """Validate required fields and return list of missing ones"""
    required_fields = {
        'patient_name': 'Patient Name',
        'home_address': 'Home Address',
        'phone': 'Phone Number',
        'date_of_birth': 'Date of Birth',
        'sex': 'Sex'
    }
    
    missing = []
    for field, display_name in required_fields.items():
        if not data.get(field):
            missing.append(display_name)
    
    return missing