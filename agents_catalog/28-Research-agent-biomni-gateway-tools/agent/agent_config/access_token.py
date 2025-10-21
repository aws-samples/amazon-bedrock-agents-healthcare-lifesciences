from .utils import get_ssm_parameter
import boto3
import requests
import os
gateway_access_token = None


async def get_gateway_access_token():
    """Get gateway access token using manual M2M flow."""
    # For IAM authentication, we don't need an OAuth token
    # The gateway will use IAM credentials from the execution role
    auth_type = os.environ.get("AUTH_TYPE", "IAM")
    
    if auth_type == "IAM":
        # Return None for IAM - the gateway client will use IAM credentials
        return None
    
    try:
        # Get credentials from SSM
        machine_client_id = get_ssm_parameter("/app/researchapp/agentcore/machine_client_id")
        machine_client_secret = get_ssm_parameter("/app/researchapp/agentcore/cognito_secret")
        cognito_domain = get_ssm_parameter("/app/researchapp/agentcore/cognito_domain")
        user_pool_id = get_ssm_parameter("/app/researchapp/agentcore/userpool_id")
        #print(user_pool_id)

        # Remove https:// if it's already in the domain
        # Clean the domain properly
        cognito_domain = cognito_domain.strip()
        if cognito_domain.startswith("https://"):
            cognito_domain = cognito_domain[8:]  # Remove "https://"
        #print(f"Cleaned domain: {repr(cognito_domain)}")
        token_url = f"https://{cognito_domain}/oauth2/token"
        #print(f"Token URL: {token_url}")  # Debug print
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



