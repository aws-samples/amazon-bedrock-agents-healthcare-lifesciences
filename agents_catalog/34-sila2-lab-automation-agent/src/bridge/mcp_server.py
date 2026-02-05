"""MCP Server for AgentCore Gateway"""
from fastapi import FastAPI, Request, Query
from typing import Dict, Any, List, Optional
import json
import os
from sila2_bridge import SiLA2Bridge
from data_buffer import DataBuffer
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize bridge with environment variable
grpc_server = os.getenv('GRPC_SERVER', 'mock-devices.sila2.local:50051')
host, port = grpc_server.rsplit(':', 1)
bridge = SiLA2Bridge(host=host, port=int(port))

# Initialize data buffer
buffer = DataBuffer(max_minutes=5)

# REST API endpoints
@app.get("/api/status/{device_id}")
async def get_device_status_api(device_id: str):
    """Get device status (including heating_status)"""
    latest = buffer.get_latest(device_id)
    if not latest:
        return {"error": "Device not found or no data"}
    return latest

@app.get("/api/history/{device_id}")
async def get_device_history_api(
    device_id: str,
    minutes: Optional[int] = Query(5, ge=1, le=60)
):
    history = buffer.get_history(device_id=device_id, minutes=minutes)
    return {
        "device_id": device_id,
        "count": len(history),
        "minutes": minutes,
        "data": history
    }

@app.get("/api/devices")
async def list_devices_api():
    devices = buffer.get_devices()
    return {"count": len(devices), "devices": devices}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "buffer_size": len(buffer.buffer),
        "devices": len(buffer.get_devices())
    }


# MCP Tool definitions
TOOLS = [
    {
        "name": "list_devices",
        "description": "List all available lab devices",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_device_info",
        "description": "Get information about a specific device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "description": "Device identifier"}
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "get_device_status",
        "description": "Get current status of a device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "description": "Device identifier"}
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "set_temperature",
        "description": "Set target temperature for a device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_temperature": {"type": "number", "description": "Target temperature in Celsius"}
            },
            "required": ["target_temperature"]
        }
    },
    {
        "name": "get_temperature",
        "description": "Get current temperature",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "subscribe_temperature",
        "description": "Subscribe to real-time temperature updates",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_heating_status",
        "description": "Get current heating status",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "abort_experiment",
        "description": "Abort current temperature control operation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Reason for aborting the experiment"}
            },
            "required": []
        }
    },
    {
        "name": "get_task_status",
        "description": "Get status of an asynchronous task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task UUID"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "get_task_info",
        "description": "Get information about a task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task UUID"}
            },
            "required": ["task_id"]
        }
    }
]

async def handle_tool_call(tool_name, arguments):
    """Handle MCP tool calls"""
    try:
        if tool_name == "list_devices":
            return bridge.list_devices()
        
        elif tool_name == "get_device_info":
            return bridge.get_device_info(arguments["device_id"])
        
        elif tool_name == "get_device_status":
            return bridge.get_device_status(arguments["device_id"])
        
        elif tool_name == "set_temperature":
            command_instance = bridge.set_temperature(arguments["target_temperature"])
            # Get the execution UUID from the command instance
            command_uuid = str(command_instance.execution_uuid)
            return {"command_uuid": command_uuid, "status": "started"}
        
        elif tool_name == "get_temperature":
            return bridge.get_current_temperature()
        
        elif tool_name == "subscribe_temperature":
            return bridge.subscribe_temperature()
        
        elif tool_name == "get_heating_status":
            return bridge.get_heating_status()
        
        elif tool_name == "abort_experiment":
            reason = arguments.get("reason", "Manual abort")
            return bridge.abort_experiment(reason)
        
        elif tool_name == "get_task_status":
            return bridge.get_task_status(arguments["task_id"])
        
        elif tool_name == "get_task_info":
            return bridge.get_task_info(arguments["task_id"])
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        raise

@app.post("/mcp")
async def handle_mcp(request: Request):
    body = await request.json()
    
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
                "result": {"tools": TOOLS},
                "id": req_id
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            if tool_name and '___' in tool_name:
                tool_name = tool_name.split('___', 1)[1]
            arguments = params.get("arguments", {})
            
            result = await handle_tool_call(tool_name, arguments)
            
            return {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": json.dumps(result)}]}, "id": req_id}
    
    return {"error": "Invalid request format"}



@app.get("/health")
async def health():
    return {'status': 'healthy'}

