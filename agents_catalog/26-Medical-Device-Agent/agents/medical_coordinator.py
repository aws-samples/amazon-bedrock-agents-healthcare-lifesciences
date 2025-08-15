from strands import Agent
from strands.models import BedrockModel

class MedicalCoordinator:
    def __init__(self, tools):
        self.system_prompt = """You are a Medical Device Coordinator AI assistant for a healthcare organization. 
        You specialize in:
        - Medical device status monitoring and management
        - Medical literature research using PubMed
        - Clinical trials information lookup
        - Providing evidence-based medical device recommendations
        
        Always provide device IDs when referencing specific equipment and cite sources when providing medical information.
        Format your responses clearly with relevant medical context."""
        
        self.model = BedrockModel(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            max_tokens=4000,
            temperature=0.1,
        )
        
        self.agent = Agent(
            model=self.model,
            system_prompt=self.system_prompt,
            tools=tools,
        )
    
    def __call__(self, message):
        return self.agent(message)
    
    @property
    def messages(self):
        return self.agent.messages
    
    @property
    def callback_handler(self):
        return self.agent.callback_handler
    
    @callback_handler.setter
    def callback_handler(self, handler):
        self.agent.callback_handler = handler