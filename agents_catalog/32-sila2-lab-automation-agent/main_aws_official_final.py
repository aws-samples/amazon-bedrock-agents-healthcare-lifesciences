#!/usr/bin/env python3
"""
SiLA2 Lab Automation Agent - AWS公式ドキュメント準拠（最終版）
AgentCore入力形式に対応
"""
import json
import logging
import requests
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
region = boto3.Session().region_name
GATEWAY_API_URL = "https://yc7bntyqha.execute-api.us-west-2.amazonaws.com/dev/tools"

@tool
def list_available_devices() -> str:
    """List all available SiLA2 laboratory devices"""
    try:
        logger.info("Calling Gateway API to list devices")
        
        response = requests.post(GATEWAY_API_URL, json={
            "tool_name": "list_available_devices",
            "parameters": {}
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                devices = data.get("devices", [])
                result = f"Found {len(devices)} SiLA2 devices:\n"
                for device in devices:
                    result += f"- {device['device_id']}: {device['device_type']} ({device['status']})\n"
                logger.info(f"Successfully listed {len(devices)} devices")
                return result
            else:
                error_msg = f"Gateway error: {data.get('error', 'Unknown error')}"
                logger.error(error_msg)
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
        
        response = requests.post(GATEWAY_API_URL, json={
            "tool_name": "get_device_status",
            "parameters": {"device_id": device_id}
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                result = str(data.get("result", "Status retrieved"))
                logger.info(f"Successfully got status for {device_id}")
                return result
            else:
                error_msg = f"Gateway error: {data.get('error', 'Unknown error')}"
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

# Create BedrockAgentCoreApp instance
app = BedrockAgentCoreApp()

# Initialize agent globally
def initialize_agent():
    """Initialize the Strands agent"""
    try:
        model = BedrockModel(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name=region,
            temperature=0.1,
            streaming=False
        )
        
        agent = Agent(
            model=model,
            system_prompt="""You are a SiLA2 Lab Automation Agent specialized in controlling laboratory equipment via SiLA2 protocol.

You have access to tools for:
- Listing available SiLA2 devices
- Getting device status information

Always use the appropriate tools to gather information before responding to user queries about laboratory equipment.""",
            tools=[list_available_devices, get_device_status]
        )
        
        logger.info("Strands agent initialized successfully")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}")
        raise

# Global agent instance
agent = initialize_agent()

@app.entrypoint
def process_request(request_data) -> str:
    """
    Main entrypoint for AgentCore Runtime
    最終版: 辞書形式の入力に対応
    """
    try:
        logger.info(f"Processing request: {type(request_data)} - {request_data}")
        
        # 入力データの処理
        if isinstance(request_data, dict):
            # 辞書形式の場合、promptキーを取得
            prompt = request_data.get('prompt', '')
            if not prompt:
                # promptキーがない場合、他のキーを確認
                prompt = request_data.get('query', request_data.get('message', str(request_data)))
        elif isinstance(request_data, str):
            # 文字列の場合はそのまま使用
            prompt = request_data
        else:
            # その他の場合は文字列に変換
            prompt = str(request_data)
        
        logger.info(f"Extracted prompt: {prompt}")
        
        if not prompt or prompt.strip() == '':
            return "Please provide a valid prompt or query."
        
        # Use the Strands agent to process the prompt
        response = agent(prompt)
        
        logger.info(f"Agent response generated successfully")
        return response
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

if __name__ == "__main__":
    logger.info("Starting SiLA2 Lab Automation Agent - AWS Official Pattern (Final)")
    logger.info("Ready to process AgentCore requests")
    
    # Run the AgentCore app
    app.run()