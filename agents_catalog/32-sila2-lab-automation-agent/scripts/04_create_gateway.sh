#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Step 5a: Create MCP Gateway ==="
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # Get configuration
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local region="${AWS_REGION:-us-west-2}"
    local execution_role_arn
    
    # Get execution role ARN from Lambda Proxy stack
    execution_role_arn=$(aws cloudformation describe-stacks \
        --stack-name sila2-lambda-proxy \
        --query 'Stacks[0].Outputs[?OutputKey==`LambdaRoleArn`].OutputValue' \
        --output text --region "$region" 2>/dev/null)
    
    if [[ -z "$execution_role_arn" ]]; then
        log_error "Failed to get Lambda role ARN from stack"
        return 1
    fi
    
    log_info "Account ID: $account_id"
    log_info "Region: $region"
    log_info "Execution Role: $execution_role_arn"
    
    # Add IAM permissions for current user
    local current_role=$(aws sts get-caller-identity --query Arn --output text | grep -oP 'assumed-role/\K[^/]+')
    if [[ -n "$current_role" ]]; then
        log_info "Adding permissions to current role: $current_role"
        aws iam put-role-policy --role-name "$current_role" --policy-name "BedrockAgentCoreAccess" --policy-document '{
          "Version": "2012-10-17",
          "Statement": [{
              "Effect": "Allow",
              "Action": ["bedrock-agentcore:*"],
              "Resource": "*"
          }]
        }' 2>/dev/null || log_info "Permission already exists for current role"
    fi
    
    # Add IAM permissions
    log_info "Adding IAM permissions..."
    local role_name=$(echo $execution_role_arn | cut -d'/' -f2)
    
    aws iam put-role-policy --role-name "$role_name" --policy-name "BedrockAgentCoreAccess" --policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
          "Effect": "Allow",
          "Action": "bedrock-agentcore:*",
          "Resource": "*"
      }]
    }' --region $region 2>/dev/null || log_info "Permission already exists"
    
    # Update trust policy
    log_info "Updating trust policy..."
    aws iam update-assume-role-policy --role-name $role_name --policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
          "Effect": "Allow",
          "Principal": {
            "Service": ["lambda.amazonaws.com", "bedrock-agentcore.amazonaws.com"]
          },
          "Action": "sts:AssumeRole"
      }]
    }' --region $region || {
        log_error "Failed to update trust policy"
        return 1
    }
    log_info "✅ Trust policy updated successfully"
    
    # Create MCP Gateway with IAM auth
    log_info "Creating MCP Gateway with IAM auth..."
    local gateway_name="sila2-gateway-$(date +%s)"
    
    IFS='|' read -r gateway_id GATEWAY_ARN gateway_url <<< "$(region="$region" gateway_name="$gateway_name" execution_role_arn="$execution_role_arn" ~/.pyenv/versions/3.10.12/bin/python3 << 'PYEOF'
import boto3
import os

client = boto3.client('bedrock-agentcore-control', region_name=os.environ['region'])
response = client.create_gateway(
    name=os.environ['gateway_name'],
    roleArn=os.environ['execution_role_arn'],
    protocolType='MCP',
    authorizerType='AWS_IAM',
    description='SiLA2 Lab Automation Gateway'
)
print(f"{response['gatewayId']}|{response['gatewayArn']}|{response['gatewayUrl']}")
PYEOF
)"
    
    log_info "Gateway ARN: $GATEWAY_ARN"
    log_info "Gateway URL: $gateway_url"
    log_info "Gateway ID: $gateway_id"
    
    # Save configuration
    cat > .gateway-config << EOF
GATEWAY_ARN="$GATEWAY_ARN"
GATEWAY_URL="$gateway_url"
GATEWAY_ID="$gateway_id"
GATEWAY_NAME="$gateway_name"
EXECUTION_ROLE_ARN="$execution_role_arn"
REGION="$region"
ACCOUNT_ID="$account_id"
EOF
    
    log_info "✅ Gateway created successfully"
}

main "$@"
