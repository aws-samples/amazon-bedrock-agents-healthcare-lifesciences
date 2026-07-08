"""
Integration tests for OAuth2 authentication.

Tests verify Cognito client credentials flow and token retrieval
for the Open Life Sciences MCP Gateway.
"""

import os
import boto3
import requests
import pytest


class TestOAuth2TokenRetrieval:
    """Test OAuth2 token retrieval from Cognito."""
    
    def test_get_oauth2_token(self):
        """
        Verify Cognito client credentials flow.
        
        This test:
        1. Retrieves Cognito configuration from SSM Parameter Store
        2. Executes POST request to Cognito token URL with client credentials
        3. Asserts response status 200, token type "Bearer", expiration 3600 seconds
        
        Requirements: 10.1
        """
        # Get AWS region and app name from environment or defaults
        app_name = os.getenv("APP_NAME", "open-life-sciences-tool")
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        
        # Initialize SSM client
        ssm = boto3.client('ssm', region_name=region)
        
        # Retrieve Cognito configuration from SSM
        try:
            client_id = ssm.get_parameter(
                Name=f'/app/{app_name}/agentcore/machine_client_id'
            )['Parameter']['Value']
            
            client_secret = ssm.get_parameter(
                Name=f'/app/{app_name}/agentcore/cognito_secret',
                WithDecryption=True
            )['Parameter']['Value']
            
            cognito_domain = ssm.get_parameter(
                Name=f'/app/{app_name}/agentcore/cognito_domain'
            )['Parameter']['Value']
            
            auth_scope = ssm.get_parameter(
                Name=f'/app/{app_name}/agentcore/cognito_auth_scope'
            )['Parameter']['Value']
        except ssm.exceptions.ParameterNotFound as e:
            pytest.fail(f"SSM parameter not found: {e}. Ensure CloudFormation stacks are deployed.")
        except Exception as e:
            pytest.fail(f"Failed to retrieve SSM parameters: {e}")
        
        # Strip protocol prefix if present for token endpoint
        cognito_domain_clean = cognito_domain.replace("https://", "")
        token_url = f"https://{cognito_domain_clean}/oauth2/token"
        
        # Request token using client credentials flow
        response = requests.post(
            token_url,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': auth_scope
            }
        )
        
        # Assert response status is 200
        assert response.status_code == 200, \
            f"Expected status 200, got {response.status_code}. Response: {response.text}"
        
        # Parse response JSON
        token_data = response.json()
        
        # Assert token type is "Bearer"
        assert 'token_type' in token_data, "Response missing 'token_type' field"
        assert token_data['token_type'] == 'Bearer', \
            f"Expected token type 'Bearer', got '{token_data['token_type']}'"
        
        # Assert access token is present
        assert 'access_token' in token_data, "Response missing 'access_token' field"
        assert len(token_data['access_token']) > 0, "Access token is empty"
        
        # Assert expiration is 3600 seconds (60 minutes)
        assert 'expires_in' in token_data, "Response missing 'expires_in' field"
        assert token_data['expires_in'] == 3600, \
            f"Expected expiration 3600 seconds, got {token_data['expires_in']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
