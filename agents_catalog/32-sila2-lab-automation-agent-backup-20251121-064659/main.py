#!/usr/bin/env python3
"""
SiLA2 Lab Automation Agent - AgentCore Runtime with Strands
Fixed implementation following AWS official patterns
"""
import json
import logging
import requests
import boto3
from strands import Agent, tool
from strands.models import BedrockModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get AWS region
region = boto3.Session().region_name
GATEWAY_API_URL = "https://jn77k8pgyh.execute-api.us-west-2.amazonaws.com/dev"

@tool
def list_available_devices() -> str:
    """List all available SiLA2 laboratory devices"""
    try:
        logger.info("Calling Gateway API to list devices")
        
        response = requests.post(f"{GATEWAY_API_URL}/list_devices", json={}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            devices = data.get("devices", [])
            if devices:
                result = f"Found {len(devices)} SiLA2 devices:\\n"
                for device in devices:
                    result += f"- {device.get('id', device.get('device_id', 'Unknown'))}: {device.get('type', device.get('device_type', 'Unknown'))} ({device.get('status', 'Unknown')})\\n"
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

@tool
def get_device_status(device_id: str) -> str:
    """Get status of a specific SiLA2 device
    
    Args:
        device_id: The ID of the device to check status for
    """
    try:
        logger.info(f"Getting status for device: {device_id}")
        
        response = requests.post(f"{GATEWAY_API_URL}/device_status", json={"device_id": device_id}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") or data.get("device_status"):
                result = str(data.get("device_status", data.get("status", "Status retrieved")))
                logger.info(f"Successfully got status for {device_id}")
                return result
            else:
                error_msg = f"Status error: {data.get('error', 'Status not available')}"
                logger.error(error_msg)
                return error_msg
        else:
            error_msg = f"Gateway HTTP error: {response.status_code}"
            logger.error(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error getting device status: {str(e)}"
        logger.error(error_msg)
        return error_msg

# Create tools list
sila2_tools = [list_available_devices, get_device_status]

# Create Bedrock model
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name=region,
    temperature=0.1,
    streaming=False
)

# Create agent with tools
agent = Agent(
    model=model,
    system_prompt="""You are a SiLA2 Lab Automation Agent specialized in controlling laboratory equipment via SiLA2 protocol.
    
You have access to tools for:
- Listing available SiLA2 devices
- Getting device status information

Always use the appropriate tools to gather information before responding to user queries about laboratory equipment.""",
    tools=sila2_tools
)

def main():
    """Main entry point - keep agent running"""
    logger.info("Starting SiLA2 Lab Automation Agent with Strands")
    
    try:
        # Test the agent with a simple query
        test_query = "List all available devices"
        logger.info(f"Testing agent with query: {test_query}")
        
        response = agent(test_query)
        logger.info(f"Agent response: {response}")
        
        # Keep the agent running
        logger.info("Agent initialized successfully, keeping runtime active...")
        
        # Simple loop to keep the process alive
        import time
        while True:
            time.sleep(60)
            logger.info("Agent runtime still active...")
            
    except Exception as e:
        logger.error(f"Failed to start agent: {str(e)}")
        raise

if __name__ == "__main__":
    main()