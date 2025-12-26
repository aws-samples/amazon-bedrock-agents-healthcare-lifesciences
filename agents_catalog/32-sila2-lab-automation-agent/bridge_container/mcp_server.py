"""MCP Server for AgentCore Gateway"""
from fastapi import FastAPI, Request
from typing import Dict, Any, List, Optional
import json

app = FastAPI()

# GrpcClientを遅延初期化
_grpc_client = None

def get_grpc_client():
    global _grpc_client
    if _grpc_client is None:
        from grpc_client import GrpcClient
        _grpc_client = GrpcClient()
    return _grpc_client

@app.post("/mcp")
async def handle_mcp(request: Request):
    body = await request.json()
    
    grpc_client = get_grpc_client()
    
    if "jsonrpc" not in body:
        tool_name = body.get('name', '')
        arguments = body.get('arguments', body if body else {})
        if tool_name and '___' in tool_name:
            tool_name = tool_name.split('___', 1)[1]
        if not tool_name:
            tool_name = "list_devices"
        body = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": body.get('id', 1)
        }
    
    if "jsonrpc" in body:
        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-10-07",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "sila2-bridge", "version": "1.0.0"}
                },
                "id": req_id
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {"name": "list_devices", "description": "List all available SiLA2 devices", "inputSchema": {"type": "object", "properties": {}}},
                        {"name": "get_device_status", "description": "Get status of a specific device", "inputSchema": {"type": "object", "properties": {"device_id": {"type": "string"}}, "required": ["device_id"]}},
                        {"name": "start_task", "description": "Start an asynchronous long-running task", "inputSchema": {"type": "object", "properties": {"device_id": {"type": "string"}, "command": {"type": "string"}, "parameters": {"type": "object"}}, "required": ["device_id", "command"]}},
                        {"name": "get_task_status", "description": "Get status of a running task", "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
                        {"name": "get_property", "description": "Get device property value", "inputSchema": {"type": "object", "properties": {"device_id": {"type": "string"}, "property_name": {"type": "string"}}, "required": ["device_id", "property_name"]}}
                    ]
                },
                "id": req_id
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            if tool_name and '___' in tool_name:
                tool_name = tool_name.split('___', 1)[1]
            arguments = params.get("arguments", {})
            
            if tool_name == "list_devices":
                result = grpc_client.list_devices()
            elif tool_name == "get_device_status":
                result = grpc_client.get_device_status(arguments.get('device_id'))
            elif tool_name == "start_task":
                device_id = arguments.get('device_id')
                command = arguments.get('command')
                parameters = arguments.get('parameters', {})
                print(f"[MCP] start_task called: device={device_id}, command={command}, params={parameters}", flush=True)
                result = grpc_client.start_task(device_id, command, parameters)
            elif tool_name == "get_task_status":
                result = grpc_client.get_task_status(arguments.get('task_id'))
            elif tool_name == "get_property":
                result = grpc_client.get_property(arguments.get('device_id'), arguments.get('property_name'))
            else:
                return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}, "id": req_id}
            
            return {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": json.dumps(result)}]}, "id": req_id}
    
    return {"error": "Invalid request format"}

@app.get("/health")
async def health():
    return {'status': 'healthy'}
