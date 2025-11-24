"""
MCP Server for SiLA2 Lab Automation Agent
Provides Model Context Protocol interface for SiLA2 tools
"""

import json
import logging
from typing import Dict, Any, List
from dataclasses import dataclass
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]

class MCPServer:
    """MCP Server for SiLA2 tools"""
    
    def __init__(self):
        self.tools = self._register_tools()
        
    def _register_tools(self) -> Dict[str, MCPTool]:
        """Register available MCP tools"""
        return {
            "sila2_device_status": MCPTool(
                name="sila2_device_status",
                description="Check the status of a SiLA2 device",
                input_schema={
                    "type": "object",
                    "properties": {
                        "device_name": {
                            "type": "string",
                            "description": "Name of the SiLA2 device"
                        }
                    },
                    "required": ["device_name"]
                }
            ),
            "sila2_execute_command": MCPTool(
                name="sila2_execute_command",
                description="Execute a command on a SiLA2 device",
                input_schema={
                    "type": "object",
                    "properties": {
                        "device_name": {
                            "type": "string",
                            "description": "Name of the SiLA2 device"
                        },
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        }
                    },
                    "required": ["device_name", "command"]
                }
            )
        }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in self.tools.values()
        ]
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool"""
        try:
            if name not in self.tools:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Unknown tool: {name}"}]
                }
            
            # Import and execute SiLA2 tools
            from .sila2_mcp_tools import execute_sila2_tool
            
            result = execute_sila2_tool(name, arguments)
            
            return {
                "content": [{"type": "text", "text": result}]
            }
            
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error: {str(e)}"}]
            }

def lambda_handler(event, context):
    """AWS Lambda handler for MCP Server"""
    try:
        server = MCPServer()
        
        # Parse MCP request
        method = event.get('method')
        params = event.get('params', {})
        
        if method == 'tools/list':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'tools': server.list_tools()
                })
            }
        
        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            
            result = server.call_tool(tool_name, arguments)
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown method: {method}'
                })
            }
            
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

if __name__ == "__main__":
    # Local testing
    server = MCPServer()
    print("Available tools:", server.list_tools())