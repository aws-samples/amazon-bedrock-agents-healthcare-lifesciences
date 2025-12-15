"""MCP Server for AgentCore Gateway"""
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from grpc_client import GrpcClient
import json

app = FastAPI()
grpc_client = GrpcClient()


class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class MCPRequest(BaseModel):
    tool_calls: List[MCPToolCall]


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


@app.post("/mcp")
async def handle_mcp(request: Request):
    body = await request.json()
    
    # Handle AgentCore Gateway formats
    # Format 1: {"name": "tool_name", "arguments": {...}}
    # Format 2: {"method": "tools/call", "params": {...}}
    # Format 3: Empty {} or arguments only
    
    # Convert Gateway format to JSON-RPC if needed
    if "jsonrpc" not in body:
        tool_name = body.get('name', '')
        arguments = body.get('arguments', body if body else {})
        
        # Remove Gateway prefix (e.g., "gateway-id___list_devices" -> "list_devices")
        if tool_name and '___' in tool_name:
            tool_name = tool_name.split('___', 1)[1]
        
        # Handle empty event - default to list_devices
        if not tool_name:
            tool_name = "list_devices"
        
        # Convert to JSON-RPC format
        body = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": body.get('id', 1)
        }
    
    # Handle JSON-RPC format
    if "jsonrpc" in body:
        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-10-07",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "sila2-bridge",
                        "version": "1.0.0"
                    }
                },
                "id": req_id
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {
                            "name": "list_devices",
                            "description": "List all available SiLA2 devices",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "get_device_status",
                            "description": "Get status of a specific device",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"device_id": {"type": "string"}},
                                "required": ["device_id"]
                            }
                        },
                        {
                            "name": "execute_command",
                            "description": "Execute a command on a device",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "device_id": {"type": "string"},
                                    "command": {"type": "string"},
                                    "parameters": {"type": "object"}
                                },
                                "required": ["device_id", "command"]
                            }
                        }
                    ]
                },
                "id": req_id
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            # Remove Gateway prefix if present (e.g., "gateway-id___list_devices" -> "list_devices")
            if tool_name and '___' in tool_name:
                tool_name = tool_name.split('___', 1)[1]
            arguments = params.get("arguments", {})
            
            if tool_name == "list_devices":
                result = grpc_client.list_devices()
            elif tool_name == "get_device_status":
                result = grpc_client.get_device_status(arguments.get('device_id'))
            elif tool_name == "execute_command":
                result = grpc_client.execute_command(
                    arguments.get('device_id'),
                    arguments.get('command'),
                    arguments.get('parameters', {})
                )
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                    "id": req_id
                }
            
            return {
                "jsonrpc": "2.0",
                "result": {"content": [{"type": "text", "text": json.dumps(result)}]},
                "id": req_id
            }
    
    # Handle custom format (backward compatibility)
    if "tool_calls" in body:
        results = []
        for tool_call in body["tool_calls"]:
            if tool_call["name"] == "list_devices":
                result = grpc_client.list_devices()
            elif tool_call["name"] == "get_device_status":
                result = grpc_client.get_device_status(tool_call["arguments"].get('device_id'))
            elif tool_call["name"] == "execute_command":
                result = grpc_client.execute_command(
                    tool_call["arguments"].get('device_id'),
                    tool_call["arguments"].get('command'),
                    tool_call["arguments"].get('parameters', {})
                )
            else:
                result = {'error': f'Unknown tool: {tool_call["name"]}'}
            results.append(result)
        return {'results': results}
    
    return {"error": "Invalid request format"}


@app.get("/health")
async def health():
    return {'status': 'healthy'}
