"""
Sample tools for the AgentCore Strands Template.
These are basic tools that can be used as examples or starting points.
"""

from typing import Dict, Any
import json
from strands import tool

@tool(
    name="Get_system_info",
    description="Gets basic system information",
)
def get_system_info() -> Dict[str, Any]:
    """
    Get basic system information.
    
    Returns:
        Dict containing system information
    """
    return {
        "status": "operational",
        "version": "1.0.0",
        "capabilities": [
            "text_processing",
            "memory_storage",
            "tool_execution"
        ]
    }


# List of available tools for easy import
SAMPLE_TOOLS = [
    get_system_info
]
