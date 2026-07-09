from strands.hooks import HookProvider, HookRegistry, BeforeInvocationEvent, AfterToolCallEvent
import logging

logger = logging.getLogger(__name__)

# Global variable to store current model_id
_current_model_id = "Unknown"

class ToolLoggerHook(HookProvider):
    def __init__(self, model_id: str = None):
        """Initialize hook with optional model_id"""
        super().__init__()
        if model_id:
            global _current_model_id
            _current_model_id = model_id
    
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.log_invocation_info)
        registry.add_callback(AfterToolCallEvent, self.log_tool_call)
    
    def log_invocation_info(self, event: BeforeInvocationEvent) -> None:
        # Log model information - try multiple ways to access model_id
        model_id = _current_model_id  # Use global as fallback
        
        if hasattr(event.agent, 'model'):
            model = event.agent.model
            # Try to get model_id from the model object
            # For BedrockModel, try these in order
            for attr in ['model_id', '_model_id', 'model', '_model']:
                if hasattr(model, attr):
                    potential_id = getattr(model, attr)
                    if potential_id and isinstance(potential_id, str):
                        model_id = potential_id
                        break
            
            # Try config
            if model_id == _current_model_id and hasattr(model, 'config'):
                if hasattr(model.config, 'model_id'):
                    model_id = model.config.model_id
                elif hasattr(model.config, 'model'):
                    model_id = model.config.model
            
            # Try kwargs
            if model_id == _current_model_id and hasattr(model, '_kwargs'):
                if 'model_id' in model._kwargs:
                    model_id = model._kwargs['model_id']
                elif 'model' in model._kwargs:
                    model_id = model._kwargs['model']
            
            # Try __dict__
            if model_id == _current_model_id and hasattr(model, '__dict__'):
                if 'model_id' in model.__dict__:
                    model_id = model.__dict__['model_id']
                elif 'model' in model.__dict__:
                    model_id = model.__dict__['model']
        
        print(f"🤖 Model: {model_id}")
        print(f"🔧 Available tools: {event.agent.tool_names}")
        logger.info(f"Invocation with model: {model_id}, tools: {event.agent.tool_names}")
    
    def log_tool_call(self, event: AfterToolCallEvent) -> None:
        # Log tool usage
        if hasattr(event, 'tool_name'):
            print(f"✅ Tool executed: {event.tool_name}")
            logger.info(f"Tool executed: {event.tool_name}")

def set_current_model_id(model_id: str):
    """Set the current model ID for logging"""
    global _current_model_id
    _current_model_id = model_id
