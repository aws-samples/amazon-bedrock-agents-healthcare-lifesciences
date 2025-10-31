from strands.hooks import HookProvider, HookRegistry, BeforeInvocationEvent, AfterToolCallEvent
import logging

logger = logging.getLogger(__name__)

class ToolLoggerHook(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.log_available_tools)
        registry.add_callback(AfterToolCallEvent, self.log_available_tools)
    
    def log_available_tools(self, event: BeforeInvocationEvent) -> None:
        print(f"Available tools loop: {event.agent.tool_names}")
