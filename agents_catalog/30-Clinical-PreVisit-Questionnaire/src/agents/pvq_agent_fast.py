"""
Fast UCLA Health Pre-Visit Questionnaire Agent
Optimized for low latency responses
"""

from strands import Agent, tool
from ..models.patient_data import PVQData

class FastPVQAgent:
    def __init__(self):
        self.pvq_data = PVQData()
        
        # Minimal system prompt for faster processing
        system_prompt = """You help complete UCLA Health questionnaire. Ask one question at a time. Use tools to save data. Be brief and direct."""

        # Use faster model and minimal tools
        self.agent = Agent(
            model="us.anthropic.claude-3-haiku-20240307-v1:0",  # Faster model
            system_prompt=system_prompt,
            tools=[
                self.save_info,
                self.save_condition,
                self.save_med,
                self.get_status,
                self.save_data
            ]
        )
    
    @tool
    def save_info(self, field: str, value: str) -> str:
        fields = {'name': 'patient_name', 'address': 'home_address', 'phone': 'phone', 'dob': 'date_of_birth', 'sex': 'sex'}
        if field.lower() in fields:
            setattr(self.pvq_data, fields[field.lower()], value)
            return f"✅ Saved {field}"
        return f"❌ Unknown field"
    
    @tool
    def save_condition(self, condition: str, year: str = "") -> str:
        entry = f"{condition} ({year})" if year else condition
        self.pvq_data.other_health_problems.append(entry)
        return f"✅ Added {condition}"
    
    @tool
    def save_med(self, name: str, dose: str = "") -> str:
        self.pvq_data.current_medications.append({"name": name, "dose": dose})
        return f"✅ Added {name}"
    
    @tool
    def get_status(self) -> str:
        return f"📋 Info: {'✅' if self.pvq_data.patient_name else '❌'} | Conditions: {len(self.pvq_data.other_health_problems)} | Meds: {len(self.pvq_data.current_medications)}"
    
    @tool
    def save_data(self) -> str:
        import json, datetime
        filename = f"data/fast_pvq_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding="utf-8") as f:
                json.dump(self.pvq_data.to_dict(), f)
            return f"💾 Saved to {filename}"
        except:
            return "❌ Save failed"
    
    def chat(self, message: str) -> str:
        """Fast chat processing"""
        try:
            msg = message.lower()
            if msg in ['quit', 'done']: 
                return self.save_data()
            if msg in ['status', 'progress']: 
                return self.get_status()
            
            result = self.agent(message)
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            return f"❌ Error: {str(e)}"
