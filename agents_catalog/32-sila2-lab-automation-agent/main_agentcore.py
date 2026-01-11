#!/usr/bin/env python3
"""
SiLA2 Lab Automation Agent - AgentCore with Lambda Direct Call
"""
import os
import boto3
import json
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
    """List all available SiLA2 laboratory devices (HPLC, centrifuge, pipette)"""
    result = call_lambda_tool("list_devices", {})
    devices = result.get("devices", [])
    return f"Found {len(devices)} devices: " + ", ".join([f"{d['id']} ({d['status']})" for d in devices])

@tool
def get_device_status(device_id: str) -> str:
    """Get device status"""
    result = call_lambda_tool("get_device_status", {"device_id": device_id})
    return f"Device {result['device_id']}: {result['status']} ({result['type']})"

@tool
def execute_control(device_id: str, command: str, parameters: dict = None) -> str:
    """Execute device control commands (set_temperature, abort_experiment)"""
    if parameters is None:
        parameters = {}
    result = call_lambda_tool("execute_control", {"device_id": device_id, "command": command, "parameters": parameters})
    if 'task_id' in result:
        return f"Task {result['task_id']} started with status: {result.get('status', 'running')}"
    elif 'error' in result:
        return f"Error: {result['error']}"
    return str(result)

@tool
def get_task_status(task_id: str) -> str:
    """Get task status"""
    result = call_lambda_tool("get_task_status", {"task_id": task_id})
    return f"Task {task_id}: {result['status']} (Progress: {result['progress']}%)"

@tool
def get_property(device_id: str, property_name: str) -> str:
    """Get device property"""
    result = call_lambda_tool("get_property", {"device_id": device_id, "property_name": property_name})
    return f"{result['property']}: {result['value']} {result.get('unit', '')}"

@tool
def analyze_heating_rate(device_id: str, history: list) -> str:
    """Calculate heating rate and detect anomalies from temperature history"""
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
            
            tools = [list_devices, get_device_status, execute_control, get_task_status, get_property, analyze_heating_rate]
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
