"""
Ultra-Fast PVQ Agent - Maximum Speed Optimization
Pre-compiled responses and minimal processing
"""

import json
import datetime
from ..models.patient_data import PVQData

class UltraFastPVQAgent:
    def __init__(self):
        self.pvq_data = PVQData()
        self.state = "basic_info"
        self.responses = {
            "greeting": "Hi! Let's complete your questionnaire quickly. What's your name?",
            "name_saved": "Got it! What's your address?",
            "address_saved": "Thanks! Phone number?",
            "phone_saved": "Perfect! Date of birth (MM/DD/YYYY)?",
            "dob_saved": "Great! Are you male or female?",
            "sex_saved": "Excellent! Any medical conditions?",
            "condition_saved": "Noted! Any medications?",
            "med_saved": "Good! Anything else or type 'done'?",
            "completed": "✅ All done! Data saved."
        }
    
    def chat(self, message: str) -> str:
        """Ultra-fast rule-based responses"""
        msg = message.lower().strip()
        
        # Quick exits
        if msg in ['done', 'quit']:
            self.save_data()
            return self.responses["completed"]
        
        if msg in ['status', 'progress']:
            return self.get_quick_status()
        
        # Rule-based processing for speed
        if self.state == "basic_info":
            return self.process_basic_info(message)
        elif self.state == "medical":
            return self.process_medical(message)
        else:
            return self.process_general(message)
    
    def process_basic_info(self, message: str) -> str:
        """Process basic info with pattern matching"""
        msg = message.lower()
        
        # Name detection
        if any(word in msg for word in ['name', 'called', 'am']):
            name = self.extract_name(message)
            if name:
                self.pvq_data.patient_name = name
                return self.responses["name_saved"]
        
        # Address detection
        if any(word in msg for word in ['live', 'address', 'street', 'ave', 'blvd']):
            self.pvq_data.home_address = message
            return self.responses["address_saved"]
        
        # Phone detection
        if any(char.isdigit() for char in msg) and len([c for c in msg if c.isdigit()]) >= 10:
            self.pvq_data.phone = message
            return self.responses["phone_saved"]
        
        # DOB detection
        if '/' in msg and any(char.isdigit() for char in msg):
            self.pvq_data.date_of_birth = message
            return self.responses["dob_saved"]
        
        # Sex detection
        if any(word in msg for word in ['male', 'female', 'man', 'woman']):
            self.pvq_data.sex = 'Male' if 'male' in msg or 'man' in msg else 'Female'
            self.state = "medical"
            return self.responses["sex_saved"]
        
        return "Please provide the requested information."
    
    def process_medical(self, message: str) -> str:
        """Process medical info quickly"""
        msg = message.lower()
        
        # Medical condition detection
        if any(word in msg for word in ['have', 'diabetes', 'pressure', 'heart', 'asthma', 'arthritis']):
            self.pvq_data.other_health_problems.append(message)
            return self.responses["condition_saved"]
        
        # Medication detection
        if any(word in msg for word in ['take', 'medication', 'pill', 'mg', 'daily']):
            self.pvq_data.current_medications.append({"name": message, "dose": ""})
            return self.responses["med_saved"]
        
        return "Any medical conditions or medications?"
    
    def process_general(self, message: str) -> str:
        """General processing"""
        self.pvq_data.other_health_problems.append(message)
        return "Got it! Anything else?"
    
    def extract_name(self, message: str) -> str:
        """Quick name extraction"""
        words = message.split()
        # Look for capitalized words after common name indicators
        name_indicators = ['name', 'am', 'called']
        for i, word in enumerate(words):
            if word.lower() in name_indicators and i + 1 < len(words):
                return ' '.join(words[i+1:i+3])  # Take next 1-2 words
        
        # Fallback: look for capitalized words
        caps = [w for w in words if w[0].isupper() and len(w) > 1]
        return ' '.join(caps[:2]) if caps else ""
    
    def get_quick_status(self) -> str:
        """Ultra-quick status"""
        return f"📋 {self.pvq_data.patient_name or 'No name'} | {len(self.pvq_data.other_health_problems)} conditions | {len(self.pvq_data.current_medications)} meds"
    
    def save_data(self) -> str:
        """Quick save"""
        try:
            filename = f"data/ultra_fast_{datetime.datetime.now().strftime('%H%M%S')}.json"
            with open(filename, 'w', encoding="utf-8") as f:
                json.dump(self.pvq_data.to_dict(), f)
            return f"💾 Saved"
        except:
            return "❌ Save failed"
