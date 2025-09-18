#!/usr/bin/python

import asyncio
import click
from bedrock_agentcore.identity.auth import requires_access_token
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
import sys
import os
import boto3
import requests
from time import sleep

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.utils import get_ssm_parameter

gateway_access_token = None


@requires_access_token(
    provider_name=get_ssm_parameter("/app/myapp/agentcore/cognito_provider"),
    scopes=[],  # Optional unless required
    auth_flow="M2M",
)
async def _get_access_token_manually(*, access_token: str):
    
    global gateway_access_token
    gateway_access_token = access_token
    
    return access_token

async def get_gateway_access_token():
    """Get gateway access token using manual M2M flow."""
    try:
        # Get credentials from SSM
        machine_client_id = get_ssm_parameter("/app/myapp/agentcore/machine_client_id")
        machine_client_secret = get_ssm_parameter("/app/myapp/agentcore/cognito_secret")
        cognito_domain = get_ssm_parameter("/app/myapp/agentcore/cognito_domain")
        user_pool_id = get_ssm_parameter("/app/myapp/agentcore/userpool_id")
        #print(user_pool_id)

        # Remove https:// if it's already in the domain
        # Clean the domain properly
        cognito_domain = cognito_domain.strip()
        if cognito_domain.startswith("https://"):
            cognito_domain = cognito_domain[8:]  # Remove "https://"
        #print(f"Cleaned domain: {repr(cognito_domain)}")
        token_url = f"https://{cognito_domain}/oauth2/token"
        #print(f"Token URL: {token_url}")  # Debug print
        sleep(2)
        #print(f"Token URL: {repr(token_url)}")
        
        # Test URL 
        from urllib.parse import urlparse
        parsed = urlparse(token_url)
        #print(f"Parsed - scheme: {parsed.scheme}, netloc: {parsed.netloc}")
        
        # Get resource server ID from machine client configuration
        try:
            cognito_client = boto3.client('cognito-idp')
            
            
            # List resource servers to find the ID
            response = cognito_client.list_resource_servers(UserPoolId=user_pool_id,MaxResults=1)
            print(response)
            if response['ResourceServers']:
                resource_server_id = response['ResourceServers'][0]['Identifier']
                #print(resource_server_id)
                scopes = f"{resource_server_id}/read"
            else:
                scopes = "gateway:read gateway:write"
        except Exception as e:
            raise Exception(f"Error getting scopes: {str(e)}")

        #print("Scope")
        #print(scopes)
        # Perform M2M OAuth flow
        token_url = f"https://{cognito_domain}/oauth2/token"
        token_data = {
            "grant_type": "client_credentials",
            "client_id": machine_client_id,
            "client_secret": machine_client_secret,
            "scope": scopes
        }
        
        response = requests.post(
            token_url, 
            data=token_data, 
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.text}")
        global gateway_access_token
        access_token=response.json()["access_token"]
        gateway_access_token = access_token
        #print(f"Gateway Access Token: {access_token}")    
        return access_token     
        
    except Exception as e:
        raise Exception(f"Error getting gateway access token: {str(e)}")




@click.command()
@click.option("--prompt", "-p", required=True, help="Prompt to send to the MCP agent")
def main(prompt: str):
    """CLI tool to interact with an MCP Agent using a prompt."""

    # Fetch access token
    #asyncio.run(_get_access_token_manually(access_token=""))
    asyncio.run(get_gateway_access_token())
    # Load gateway configuration from SSM parameters
    try:
        gateway_url = get_ssm_parameter("/app/myapp/agentcore/gateway_url")
    except Exception as e:
        print(f"❌ Error reading gateway URL from SSM: {str(e)}")
        sys.exit(1)

    print(f"Gateway Endpoint - MCP URL: {gateway_url}")

    # Set up MCP client
    client = MCPClient(
        lambda: streamablehttp_client(
            gateway_url,
            headers={"Authorization": f"Bearer {gateway_access_token}"},
        )
    )

    with client:
        agent = Agent(tools=client.list_tools_sync())
        response = agent(prompt)
        print(str(response))


if __name__ == "__main__":
    main()