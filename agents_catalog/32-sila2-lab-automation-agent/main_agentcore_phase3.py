#!/usr/bin/env python3
"""
SiLA2 Lab Automation Agent - AgentCore with Gateway
"""
import logging
import os
import boto3
from bedrock_agentcore import BedrockAgentCoreApp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

GATEWAY_URL = os.getenv('GATEWAY_URL', 'https://sila2-gateway-1764231790-6an1qmwnun.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp')
MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

strands_available = False
mcp_client = None

logger.info(f"🔧 Gateway URL: {GATEWAY_URL}")
logger.info(f"🔧 Model ID: {MODEL_ID}")

try:
    from strands import Agent
    from strands.models import BedrockModel
    from strands.tools.mcp.mcp_client import MCPClient
    from mcp.client.streamable_http import streamablehttp_client
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    import httpx
    from typing import Generator
    
    class SigV4HTTPXAuth(httpx.Auth):
        def __init__(self, credentials, service: str, region: str):
            self.credentials = credentials
            self.service = service
            self.region = region
            self.signer = SigV4Auth(credentials, service, region)
        
        def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
            headers = dict(request.headers)
            headers.pop("connection", None)
            
            aws_request = AWSRequest(
                method=request.method,
                url=str(request.url),
                data=request.content,
                headers=headers,
            )
            self.signer.add_auth(aws_request)
            request.headers.update(dict(aws_request.headers))
            yield request
    
    def _create_transport():
        session = boto3.Session()
        credentials = session.get_credentials()
        region = session.region_name or 'us-west-2'
        
        auth = SigV4HTTPXAuth(credentials, 'bedrock-agentcore', region)
        return streamablehttp_client(GATEWAY_URL, auth=auth)
    
    mcp_client = MCPClient(_create_transport)
    strands_available = True
    logger.info("✅ Strands initialized with SigV4 auth")
except Exception as e:
    logger.warning(f"⚠️ Strands not available: {e}")

@app.entrypoint
def process_request(request_data) -> str:
    logger.info("🚀 Entrypoint called")
    
    try:
        if isinstance(request_data, dict):
            query = request_data.get('prompt', request_data.get('query', str(request_data)))
        else:
            query = str(request_data)
        
        if not query or query.strip() == '':
            return "Please provide a valid query."
        
        logger.info(f"Query: {query}")
        
        if strands_available and mcp_client:
            from strands.models import BedrockModel
            from strands import Agent
            
            bedrock_model = BedrockModel(
                inference_profile_id=MODEL_ID,
                temperature=0.0,
                streaming=True
            )
            
            with mcp_client:
                tools = mcp_client.list_tools_sync()
                logger.info(f"Loaded {len(tools)} tools")
                agent = Agent(model=bedrock_model, tools=tools)
                response = agent(query)
                logger.info("✅ Completed")
                return str(response)
        else:
            return f"Fallback mode: {query}"
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return f"Error: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting SiLA2 Agent")
    app.run()
