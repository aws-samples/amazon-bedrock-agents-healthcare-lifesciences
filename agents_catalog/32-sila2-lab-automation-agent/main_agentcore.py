#!/usr/bin/env python3
"""
SiLA2 Lab Automation Agent - AgentCore with Lambda Direct Call
"""
import os
import boto3
import json
from typing import List, Dict, Any
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

LAMBDA_FUNCTION = os.getenv('LAMBDA_FUNCTION', 'sila2-mcp-proxy')
ANALYZE_LAMBDA_FUNCTION = os.getenv('ANALYZE_LAMBDA_FUNCTION', 'sila2-analyze-heating-rate')
REGION = os.getenv('AWS_REGION', 'us-west-2')
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

lambda_client = boto3.client('lambda', region_name=REGION)

strands_available = False
try:
    from strands import Agent, tool
    from strands.models import BedrockModel
    strands_available = True
except Exception:
    pass

def call_lambda_tool(tool_name: str, arguments: dict) -> dict:
    """Call Lambda function with MCP tool request"""
    # analyze_heating_rate uses separate Lambda
    function_name = ANALYZE_LAMBDA_FUNCTION if tool_name == 'analyze_heating_rate' else LAMBDA_FUNCTION
    
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
        "id": 1
    }
    
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    if 'result' in result and 'content' in result['result']:
        return json.loads(result['result']['content'][0]['text'])
    return result

@tool
def list_devices() -> str:
    """List all available SiLA2 laboratory devices"""
    result = call_lambda_tool("list_devices", {})
    return json.dumps(result)

@tool
def get_device_info(device_id: str) -> str:
    """Get information about a specific device"""
    result = call_lambda_tool("get_device_info", {"device_id": device_id})
    return json.dumps(result)

@tool
def get_device_status(device_id: str) -> str:
    """Get current status of a device"""
    result = call_lambda_tool("get_device_status", {"device_id": device_id})
    return json.dumps(result)

@tool
def set_temperature(target_temperature: float) -> str:
    """Set target temperature for a device"""
    result = call_lambda_tool("set_temperature", {"target_temperature": target_temperature})
    return json.dumps(result)

@tool
def get_temperature() -> str:
    """Get current temperature"""
    result = call_lambda_tool("get_temperature", {})
    return json.dumps(result)

@tool
def subscribe_temperature() -> str:
    """Subscribe to real-time temperature updates"""
    result = call_lambda_tool("subscribe_temperature", {})
    return json.dumps(result)

@tool
def get_heating_status() -> str:
    """Get current heating status"""
    result = call_lambda_tool("get_heating_status", {})
    return json.dumps(result)

@tool
def abort_experiment() -> str:
    """Abort current temperature control operation"""
    result = call_lambda_tool("abort_experiment", {})
    return json.dumps(result)

@tool
def get_task_status(task_id: str) -> str:
    """Get status of an asynchronous task"""
    result = call_lambda_tool("get_task_status", {"task_id": task_id})
    return json.dumps(result)

@tool
def get_task_info(task_id: str) -> str:
    """Get information about a task"""
    result = call_lambda_tool("get_task_info", {"task_id": task_id})
    return json.dumps(result)

@tool
def analyze_heating_rate(device_id: str, history: List[Dict[str, Any]]) -> str:
    """Calculate heating rate and detect anomalies from temperature history
    
    Args:
        device_id: Device identifier
        history: List of temperature readings with timestamps
    """
    result = call_lambda_tool("analyze_heating_rate", {"device_id": device_id, "history": history})
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
                analyze_heating_rate
            ]
            agent = Agent(
                model=bedrock_model,
                tools=tools,
                system_prompt=system_prompt
            )
            
            response = agent(query)
            yield response.message['content'][0]['text']
        else:
            yield f"Fallback mode: {query}"
    
    except Exception as e:
        yield f"Error: {str(e)}"

if __name__ == "__main__":
    app.run()
