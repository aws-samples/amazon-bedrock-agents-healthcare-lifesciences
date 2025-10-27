from strands.hooks import HookProvider, HookRegistry, BeforeInvocationEvent
import logging

logger = logging.getLogger(__name__)

class ToolLoggerHook(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.log_available_tools)
    
    def log_available_tools(self, event: BeforeInvocationEvent) -> None:
        logger.info(f"Available tools at start of agent loop: {event.agent.tool_names}")
    
