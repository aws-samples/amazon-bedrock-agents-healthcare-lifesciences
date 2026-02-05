#!/usr/bin/env python3
"""
SiLA2 Lab Automation Agent - AgentCore with Gateway Integration
"""
import os
import boto3
import json
import requests
from typing import List, Dict, Any
from datetime import datetime
from aws_requests_auth.aws_auth import AWSRequestsAuth
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

REGION = os.getenv('AWS_REGION', 'us-west-2')
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
MEMORY_ID = os.getenv('MEMORY_ID', 'sila2_memory-NajlMR3ROI')
GATEWAY_URL = os.getenv('GATEWAY_URL', 'https://sila2-gateway-1770265126-gc1ge4l0eo.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp')

strands_available = False
try:
    from strands import Agent, tool
    from strands.models import BedrockModel
    from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
    from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
    strands_available = True
except Exception:
    pass

def call_gateway_tool(tool_name: str, arguments: dict) -> dict:
    """Call tool through AgentCore Gateway with AWS SigV4 authentication"""
    if not GATEWAY_URL:
        raise ValueError("GATEWAY_URL environment variable not set")
    
    # Prepare MCP request payload
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }
    
    # AWS SigV4 authentication
    session = boto3.Session()
    credentials = session.get_credentials()
    auth = AWSRequestsAuth(
        aws_access_key=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        aws_token=credentials.token,
        aws_host=GATEWAY_URL.replace('https://', '').replace('http://', '').split('/')[0],
        aws_region=REGION,
        aws_service='bedrock-agentcore'
    )
    
    # Make authenticated request to Gateway
    response = requests.post(
        GATEWAY_URL,
        json=payload,
        auth=auth,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    response.raise_for_status()
    result = response.json()
    
    # Parse MCP response
    if 'result' in result and 'content' in result['result']:
        return json.loads(result['result']['content'][0]['text'])
    return result

@tool
def list_devices() -> str:
    """List all available SiLA2 laboratory devices"""
    result = call_gateway_tool("sila2-bridge-container___list_devices", {})
    return json.dumps(result)

@tool
def get_device_info(device_id: str) -> str:
    """Get information about a specific device"""
    result = call_gateway_tool("sila2-bridge-container___get_device_info", {"device_id": device_id})
    return json.dumps(result)

@tool
def get_device_status(device_id: str) -> str:
    """Get current status of a device"""
    result = call_gateway_tool("sila2-bridge-container___get_device_status", {"device_id": device_id})
    return json.dumps(result)

@tool
def set_temperature(target_temperature: float) -> str:
    """Set target temperature for a device"""
    result = call_gateway_tool("sila2-bridge-container___set_temperature", {"target_temperature": target_temperature})
    return json.dumps(result)

@tool
def get_temperature() -> str:
    """Get current temperature"""
    result = call_gateway_tool("sila2-bridge-container___get_temperature", {})
    return json.dumps(result)

@tool
def subscribe_temperature() -> str:
    """Subscribe to real-time temperature updates"""
    result = call_gateway_tool("sila2-bridge-container___subscribe_temperature", {})
    return json.dumps(result)

@tool
def get_heating_status() -> str:
    """Get current heating status"""
    result = call_gateway_tool("sila2-bridge-container___get_heating_status", {})
    return json.dumps(result)

@tool
def abort_experiment() -> str:
    """Abort current temperature control operation"""
    result = call_gateway_tool("sila2-bridge-container___abort_experiment", {})
    return json.dumps(result)

@tool
def get_task_status(task_id: str) -> str:
    """Get status of an asynchronous task"""
    result = call_gateway_tool("sila2-bridge-container___get_task_status", {"task_id": task_id})
    return json.dumps(result)

@tool
def get_task_info(task_id: str) -> str:
    """Get information about a task"""
    result = call_gateway_tool("sila2-bridge-container___get_task_info", {"task_id": task_id})
    return json.dumps(result)

@tool
def execute_control(device_id: str, action: str) -> str:
    """Execute control action on device (e.g., abort experiment)
    
    Args:
        device_id: Device identifier
        action: Control action ("abort")
    """
    if action == "abort":
        result = call_gateway_tool("sila2-bridge-container___abort_experiment", {})
    else:
        result = {"error": f"Unknown action: {action}"}
    return json.dumps(result)

@tool
def analyze_heating_rate(device_id: str, history: List[Dict[str, Any]]) -> str:
    """Calculate heating rate and detect anomalies from temperature history
    
    Args:
        device_id: Device identifier
        history: List of temperature readings with timestamps
    """
    result = call_gateway_tool("analyze-heating-rate___analyze_heating_rate", {"device_id": device_id, "history": history})
    return json.dumps(result)

@app.entrypoint
async def process_request(request_data):
    try:
        if isinstance(request_data, dict):
            query = request_data.get('prompt', request_data.get('query', str(request_data)))
        else:
            query = str(request_data)
        
        if not query or query.strip() == '':
            yield "Please provide a valid query."
            return
        
        if strands_available:
            # Load agent instructions from file
            instructions_path = os.path.join(os.path.dirname(__file__), 'agentcore', 'agent_instructions.txt')
            try:
                with open(instructions_path, 'r') as f:
                    system_prompt = f.read()
            except FileNotFoundError:
                system_prompt = "You are a SiLA2 laboratory automation assistant. Always use the available tools to answer questions about devices and tasks."
            
            bedrock_model = BedrockModel(
                inference_profile_id=MODEL_ID,
                temperature=0.0,
                streaming=True
            )
            
            tools = [
                list_devices, get_device_info, get_device_status,
                set_temperature, get_temperature, subscribe_temperature,
                get_heating_status, abort_experiment,
                get_task_status, get_task_info,
                analyze_heating_rate, execute_control  # Added execute_control
            ]
            
            # Configure agent with memory session manager
            agent_config = {
                'model': bedrock_model,
                'tools': tools,
                'system_prompt': system_prompt
            }
            
            # Enable memory recording with session manager if MEMORY_ID is provided
            if MEMORY_ID:
                ACTOR_ID = "hplc"
                SESSION_ID = f"hplc-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                agentcore_memory_config = AgentCoreMemoryConfig(
                    memory_id=MEMORY_ID,
                    session_id=SESSION_ID,
                    actor_id=ACTOR_ID
                )
                
                session_manager = AgentCoreMemorySessionManager(
                    agentcore_memory_config=agentcore_memory_config,
                    region_name=REGION
                )
                
                agent_config['session_manager'] = session_manager
            
            agent = Agent(**agent_config)
            
            response = agent(query)
            yield response.message['content'][0]['text']
        else:
            yield f"Fallback mode: {query}"
    
    except Exception as e:
        yield f"Error: {str(e)}"

if __name__ == "__main__":
    app.run()
