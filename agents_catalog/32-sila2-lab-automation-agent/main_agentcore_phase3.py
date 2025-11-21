#!/usr/bin/env python3
"""
SiLA2 Lab Automation Agent - Phase 3 AgentCore Runtime
AWS公式ドキュメント準拠実装
"""
import json
import logging
import requests
import boto3
import os
from bedrock_agentcore import BedrockAgentCoreApp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get AWS region
region = boto3.Session().region_name

# Phase 3 API Gateway URL - from environment variable
GATEWAY_API_URL = os.environ.get('API_GATEWAY_URL')
logger.info(f"Using API Gateway URL: {GATEWAY_API_URL}")

def list_available_devices() -> str:
    """List all available SiLA2 laboratory devices"""
    try:
        logger.info("Calling Gateway API to list devices")
        
        response = requests.post(f"{GATEWAY_API_URL}/devices", json={"action": "list"}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            devices = data.get("devices", [])
            if devices:
                result = f"Found {len(devices)} SiLA2 devices:\n"
                for device in devices:
                    result += f"- {device.get('id', device.get('device_id', 'Unknown'))}: {device.get('type', device.get('device_type', 'Unknown'))} ({device.get('status', 'Unknown')})\n"
                logger.info(f"Successfully listed {len(devices)} devices")
                return result
            else:
                error_msg = f"No devices found: {data.get('error', 'No devices available')}"
                logger.warning(error_msg)
                return error_msg
        else:
            error_msg = f"Gateway HTTP error: {response.status_code}"
            logger.error(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error listing devices: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_device_status(device_id: str) -> str:
    """Get status of a specific SiLA2 device"""
    try:
        logger.info(f"Getting status for device: {device_id}")
        
        response = requests.post(f"{GATEWAY_API_URL}/devices", json={"action": "status", "device_id": device_id}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            result = f"Device {device_id} status: {data.get('status', 'Unknown')}"
            if 'temperature' in data:
                result += f", Temperature: {data['temperature']}°C"
            logger.info(f"Successfully got status for {device_id}")
            return result
        else:
            error_msg = f"Gateway HTTP error: {response.status_code}"
            logger.error(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error getting device status: {str(e)}"
        logger.error(error_msg)
        return error_msg

def execute_device_command(device_id: str, command: str) -> str:
    """Execute a command on a SiLA2 device"""
    try:
        logger.info(f"Executing command '{command}' on device: {device_id}")
        
        response = requests.post(f"{GATEWAY_API_URL}/devices", 
                               json={"action": "command", "device_id": device_id, "command": command}, 
                               timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            result = f"Command '{command}' executed on {device_id}: {data.get('result', 'Success')}"
            logger.info(f"Successfully executed command on {device_id}")
            return result
        else:
            error_msg = f"Gateway HTTP error: {response.status_code}"
            logger.error(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error executing device command: {str(e)}"
        logger.error(error_msg)
        return error_msg

# Create BedrockAgentCoreApp instance
app = BedrockAgentCoreApp()

@app.entrypoint
def process_request(request_data) -> str:
    """
    Main entrypoint for AgentCore Runtime
    AWS公式ドキュメント準拠実装
    """
    try:
        logger.info(f"Processing request: {type(request_data)} - {request_data}")
        
        # Process input data
        if isinstance(request_data, dict):
            prompt = request_data.get('prompt', '')
            if not prompt:
                prompt = request_data.get('query', request_data.get('message', str(request_data)))
        elif isinstance(request_data, str):
            prompt = request_data
        else:
            prompt = str(request_data)
        
        logger.info(f"Extracted prompt: {prompt}")
        
        if not prompt or prompt.strip() == '':
            return "Please provide a valid prompt or query."
        
        # Simple rule-based processing for SiLA2 commands
        prompt_lower = prompt.lower()
        
        if 'list' in prompt_lower and ('device' in prompt_lower or 'equipment' in prompt_lower):
            return list_available_devices()
        elif 'status' in prompt_lower:
            # Extract device ID if mentioned
            words = prompt.split()
            device_id = None
            for word in words:
                if word.upper().startswith(('HPLC', 'CENTRIFUGE', 'PIPETTE')):
                    device_id = word.upper()
                    break
            
            if device_id:
                return get_device_status(device_id)
            else:
                return "Please specify a device ID for status check (e.g., HPLC-01, CENTRIFUGE-01, PIPETTE-01)"
        elif 'execute' in prompt_lower or 'command' in prompt_lower or 'run' in prompt_lower:
            # Extract device ID and command
            words = prompt.split()
            device_id = None
            command = "start"  # default command
            
            for word in words:
                if word.upper().startswith(('HPLC', 'CENTRIFUGE', 'PIPETTE')):
                    device_id = word.upper()
                    break
            
            if 'start' in prompt_lower:
                command = "start"
            elif 'stop' in prompt_lower:
                command = "stop"
            elif 'reset' in prompt_lower:
                command = "reset"
            
            if device_id:
                return execute_device_command(device_id, command)
            else:
                return "Please specify a device ID for command execution (e.g., HPLC-01, CENTRIFUGE-01, PIPETTE-01)"
        else:
            # General help response
            return """I'm a SiLA2 Lab Automation Agent. I can help you with:

1. List available devices: "List all devices" or "Show lab equipment"
2. Check device status: "Get status of HPLC-01" or "Check CENTRIFUGE-01 status"  
3. Execute commands: "Start PIPETTE-01" or "Stop HPLC-01"

Available devices: HPLC-01, CENTRIFUGE-01, PIPETTE-01
Available commands: start, stop, reset"""
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

if __name__ == "__main__":
    logger.info("Starting SiLA2 Lab Automation Agent Phase 3")
    logger.info("Ready to process AgentCore requests")
    
    # Run the AgentCore app
    app.run()