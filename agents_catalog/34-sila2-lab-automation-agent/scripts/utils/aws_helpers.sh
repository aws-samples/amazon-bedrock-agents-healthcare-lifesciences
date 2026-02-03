#!/bin/bash

AWS_HELPERS_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$AWS_HELPERS_SCRIPT_DIR/common.sh"

deploy_cloudformation() {
    local template_file="$1"
    local stack_name="$2"
    
    log_info "Deploying CloudFormation stack: $stack_name"
    
    if check_stack_exists "$stack_name"; then
        aws cloudformation delete-stack --stack-name "$stack_name" --region "$AWS_REGION"
        aws cloudformation wait stack-delete-complete --stack-name "$stack_name" --region "$AWS_REGION"
    fi
    
    aws cloudformation create-stack \
        --stack-name "$stack_name" \
        --template-body "file://$template_file" \
        --capabilities CAPABILITY_IAM \
        --region "$AWS_REGION"
    
    aws cloudformation wait stack-create-complete \
        --stack-name "$stack_name" \
        --region "$AWS_REGION"
}

deploy_lambda() {
    local function_name="$1"
    local zip_file="$2"
    local env_vars="$3"
    
    if aws lambda get-function --function-name "$function_name" --region "$AWS_REGION" >/dev/null 2>&1; then
        aws lambda update-function-code \
            --function-name "$function_name" \
            --zip-file "fileb://$zip_file" \
            --region "$AWS_REGION"
        
        log_info "✅ Updated Lambda function: $function_name"
    else
        log_warn "Lambda function not found: $function_name"
    fi
}

create_lambda_package() {
    local package_name="$1"
    local files="$2"
    
    log_info "Creating package: ${package_name}.zip"
    
    local temp_dir=$(mktemp -d)
    
    for file in $files; do
        if [[ -f "$file" ]]; then
            cp "$file" "$temp_dir/"
        else
            log_warn "File not found: $file"
        fi
    done
    
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt -t "$temp_dir/" --quiet 2>/dev/null || true
    fi
    
    if [[ -f "sila2_basic_pb2.py" ]]; then
        cp sila2_basic_pb2.py sila2_basic_pb2_grpc.py "$temp_dir/" 2>/dev/null || true
    fi
    
    cd "$temp_dir"
    zip -r "${OLDPWD}/${package_name}.zip" . >/dev/null 2>&1
    cd "$OLDPWD"
    
    rm -rf "$temp_dir"
}

create_ecr_repository() {
    local repo_name="$1"
    
    log_info "Creating ECR repository: $repo_name"
    aws ecr create-repository \
        --repository-name "$repo_name" \
        --region "$AWS_REGION" 2>/dev/null || log_info "ECR repository already exists"
}

setup_iam_permissions() {
    local stack_name="$1"
    
    log_info "Setting up IAM permissions for AgentCore"
    
    # Get execution role from CloudFormation
    local execution_role=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`LambdaExecutionRoleArn`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [[ -z "$execution_role" || "$execution_role" == "None" ]]; then
        # Fallback: find role by pattern
        execution_role=$(aws iam list-roles \
            --query "Roles[?contains(RoleName, 'DeviceApiLambdaRole')].Arn" \
            --output text | head -1)
    fi
    
    if [[ -n "$execution_role" ]]; then
        local role_name=$(echo "$execution_role" | cut -d'/' -f2)
        log_info "Found execution role: $role_name"
        
        # Add ECR permissions
        aws iam attach-role-policy \
            --role-name "$role_name" \
            --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess 2>/dev/null || true
        
        # Add X-Ray permissions
        aws iam attach-role-policy \
            --role-name "$role_name" \
            --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess 2>/dev/null || true
        
        # Add Bedrock permissions
        aws iam attach-role-policy \
            --role-name "$role_name" \
            --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess 2>/dev/null || true
        
        # Add Bedrock AgentCore permissions
        cat > /tmp/agentcore_policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateGatewayTarget",
        "bedrock-agentcore:GetGatewayTarget",
        "bedrock-agentcore:ListGatewayTargets"
      ],
      "Resource": "*"
    }
  ]
}
EOF
        
        aws iam put-role-policy \
            --role-name "$role_name" \
            --policy-name "BedrockAgentCoreAccess" \
            --policy-document file:///tmp/agentcore_policy.json 2>/dev/null || true
        
        rm -f /tmp/agentcore_policy.json
        
        # Update trust policy for AgentCore
        cat > /tmp/agentcore_trust_policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
        
        aws iam update-assume-role-policy \
            --role-name "$role_name" \
            --policy-document file:///tmp/agentcore_trust_policy.json 2>/dev/null || true
        
        rm -f /tmp/agentcore_trust_policy.json
        log_info "✅ IAM permissions configured for: $role_name"
    else
        log_warn "Could not find execution role for IAM setup"
    fi
}

update_lambda_functions() {
    log_info "Updating Lambda function code..."
    
    deploy_lambda "mock-hplc-device-dev" "mock_hplc_device.zip" '{"DEVICE_ID":"HPLC-01","DEVICE_MODE":"mock"}'
    deploy_lambda "mock-centrifuge-device-dev" "mock_centrifuge_device.zip" '{"DEVICE_ID":"CENTRIFUGE-01","DEVICE_MODE":"mock"}'
    deploy_lambda "mock-pipette-device-dev" "mock_pipette_device.zip" '{"DEVICE_ID":"PIPETTE-01","DEVICE_MODE":"mock"}'
    deploy_lambda "mcp-grpc-bridge-dev" "mcp_grpc_bridge.zip" '{"DEVICE_MODE":"mock","GRPC_SUPPORT":"true"}'
    deploy_lambda "device-discovery-dev" "device_discovery.zip" '{"DEVICE_MODE":"mock","LOG_LEVEL":"INFO"}'
}