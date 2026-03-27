#!/usr/bin/env python
"""Add gateway target to existing gateway."""
import boto3
import json
from scripts.utils import get_ssm_parameter, put_ssm_parameter, load_api_spec, get_cognito_client_secret

REGION = "us-east-1"
gateway_client = boto3.client("bedrock-agentcore-control", region_name=REGION)

# Get gateway ID
gateway_id = "myapp-gw-6cnltmtuhn"

# Load API spec
api_spec = load_api_spec("prerequisite/lambda/api_spec.json")

# Create target configuration
lambda_target_config = {
    "mcp": {
        "lambda": {
            "lambdaArn": get_ssm_parameter("/app/myapp/agentcore/lambda_arn"),
            "toolSchema": {"inlinePayload": api_spec},
        }
    }
}

credential_config = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]

print(f"Creating gateway target for gateway: {gateway_id}")

try:
    create_target_response = gateway_client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="LambdaUsingSDK",
        description="Lambda Target using SDK",
        targetConfiguration=lambda_target_config,
        credentialProviderConfigurations=credential_config,
    )
    
    print(f"✅ Gateway target created: {create_target_response['targetId']}")
    
    # Get gateway details
    gateway_response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
    
    # Save gateway details to SSM parameters
    put_ssm_parameter("/app/myapp/agentcore/gateway_id", gateway_id)
    put_ssm_parameter("/app/myapp/agentcore/gateway_name", "myapp-gw")
    put_ssm_parameter("/app/myapp/agentcore/gateway_arn", gateway_response["gatewayArn"])
    put_ssm_parameter("/app/myapp/agentcore/gateway_url", gateway_response["gatewayUrl"])
    put_ssm_parameter(
        "/app/myapp/agentcore/cognito_secret",
        get_cognito_client_secret(),
        with_encryption=True,
    )
    
    print("✅ Gateway configuration saved to SSM parameters")
    print(f"Gateway URL: {gateway_response['gatewayUrl']}")
    
except Exception as e:
    print(f"❌ Error: {e}")
