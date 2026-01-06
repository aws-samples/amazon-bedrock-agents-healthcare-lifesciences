#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

source "$SCRIPT_DIR/utils/common.sh"

print_header "Deploying ECS Service Discovery Stack"

REGION=${AWS_REGION:-us-east-1}
STACK_NAME=${STACK_NAME:-sila2-bridge-ecs}
ENV_NAME=${ENV_NAME:-dev}

print_info "Region: $REGION"
print_info "Stack: $STACK_NAME"
print_info "Environment: $ENV_NAME"

# VPC/Subnet取得
print_step "Getting VPC and Subnet information"
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' --output text --region $REGION)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[0:2].SubnetId' --output text --region $REGION | tr '\t' ',')

print_info "VPC: $VPC_ID"
print_info "Subnets: $SUBNET_IDS"

# CloudFormationデプロイ (ECS)
print_step "Deploying ECS CloudFormation stack"
aws cloudformation deploy \
  --template-file "$PROJECT_ROOT/infrastructure/bridge_container_ecs_no_alb.yaml" \
  --stack-name $STACK_NAME \
  --parameter-overrides \
    VpcId=$VPC_ID \
    SubnetIds=$SUBNET_IDS \
    EnvironmentName=$ENV_NAME \
  --capabilities CAPABILITY_IAM \
  --region $REGION

# Lambda Proxyデプロイ
print_step "Deploying Lambda Proxy"
BRIDGE_SG=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`BridgeSecurityGroup`].OutputValue' \
  --output text \
  --region $REGION)

aws cloudformation deploy \
  --template-file "$PROJECT_ROOT/infrastructure/lambda_proxy.yaml" \
  --stack-name sila2-lambda-proxy \
  --parameter-overrides \
    VpcId=$VPC_ID \
    PrivateSubnets=$SUBNET_IDS \
    BridgeSecurityGroup=$BRIDGE_SG \
  --capabilities CAPABILITY_IAM \
  --region $REGION

# Lambda Proxyコードを更新
print_step "Updating Lambda Proxy code with latest implementation"
cd "$PROJECT_ROOT/lambda_proxy"
zip -r /tmp/lambda-proxy.zip . >/dev/null 2>&1
aws lambda update-function-code \
  --function-name sila2-mcp-proxy \
  --zip-file fileb:///tmp/lambda-proxy.zip \
  --region $REGION >/dev/null
rm /tmp/lambda-proxy.zip
print_info "Lambda code updated successfully"

# Output取得
print_step "Getting stack outputs"
ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`BridgeServiceEndpoint`].OutputValue' \
  --output text \
  --region $REGION)

# Lambda ARN取得
LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name sila2-lambda-proxy \
  --query 'Stacks[0].Outputs[?OutputKey==`ProxyFunctionArn`].OutputValue' \
  --output text \
  --region $REGION)

# Get Bridge Service Discovery DNS name
print_step "Getting Bridge Service Discovery endpoint"
BRIDGE_DNS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`BridgeServiceEndpoint`].OutputValue' \
  --output text \
  --region $REGION)

if [[ -z "$BRIDGE_DNS" ]]; then
    BRIDGE_DNS="http://bridge.sila2.local:8080"
    print_warning "Using default Bridge DNS: $BRIDGE_DNS"
else
    print_info "Bridge DNS: $BRIDGE_DNS"
fi

# Phase 6: Deploy SNS + Lambda + EventBridge
print_step "Deploying Phase 6 infrastructure (SNS + Lambda + EventBridge)"

if [[ -f "$PROJECT_ROOT/infrastructure/phase6-cfn.yaml" ]]; then
    # Get Agent IDs if available
    AGENT_ID=${AGENTCORE_AGENT_ID:-"placeholder-agent-id"}
    ALIAS_ID=${AGENTCORE_ALIAS_ID:-"placeholder-alias-id"}
    
    # Get VPC and Subnet info from ECS stack
    VPC_ID=$(aws cloudformation describe-stacks \
      --stack-name $STACK_NAME \
      --query 'Stacks[0].Parameters[?ParameterKey==`VpcId`].ParameterValue' \
      --output text \
      --region $REGION)
    
    SUBNET_IDS=$(aws cloudformation describe-stacks \
      --stack-name $STACK_NAME \
      --query 'Stacks[0].Parameters[?ParameterKey==`SubnetIds`].ParameterValue' \
      --output text \
      --region $REGION)
    
    BRIDGE_SG=$(aws cloudformation describe-stacks \
      --stack-name $STACK_NAME \
      --query 'Stacks[0].Outputs[?OutputKey==`BridgeSecurityGroup`].OutputValue' \
      --output text \
      --region $REGION)
    
    print_info "VPC: $VPC_ID"
    print_info "Subnets: $SUBNET_IDS"
    print_info "Bridge SG: $BRIDGE_SG"
    
    aws cloudformation deploy \
      --template-file "$PROJECT_ROOT/infrastructure/phase6-cfn.yaml" \
      --stack-name sila2-phase6-stack \
      --parameter-overrides \
        BridgeURL="$BRIDGE_DNS" \
        AgentCoreAgentId="$AGENT_ID" \
        AgentCoreAliasId="$ALIAS_ID" \
        VpcId="$VPC_ID" \
        PrivateSubnetIds="$SUBNET_IDS" \
        BridgeSecurityGroupId="$BRIDGE_SG" \
      --capabilities CAPABILITY_IAM \
      --region $REGION
    
    # Get SNS Topic ARN
    SNS_TOPIC_ARN=$(aws cloudformation describe-stacks \
      --stack-name sila2-phase6-stack \
      --query 'Stacks[0].Outputs[?OutputKey==`SNSTopicArn`].OutputValue' \
      --output text \
      --region $REGION)
    
    print_info "SNS Topic ARN: $SNS_TOPIC_ARN"
    
    # Update Lambda code
    if [[ -d "$PROJECT_ROOT/lambda/invoker" ]]; then
        cd "$PROJECT_ROOT/lambda/invoker"
        
        # Create Lambda Layer for requests library
        print_info "Creating Lambda Layer for requests library..."
        LAYER_DIR="/tmp/lambda-layer-requests"
        rm -rf "$LAYER_DIR"
        mkdir -p "$LAYER_DIR/python"
        pip3 install requests -t "$LAYER_DIR/python" --quiet 2>/dev/null
        
        cd "$LAYER_DIR"
        zip -r /tmp/requests-layer.zip python/ >/dev/null 2>&1
        
        LAYER_ARN=$(aws lambda publish-layer-version \
          --layer-name sila2-requests-layer \
          --zip-file fileb:///tmp/requests-layer.zip \
          --compatible-runtimes python3.10 python3.11 \
          --region $REGION \
          --query 'LayerVersionArn' \
          --output text 2>/dev/null || echo "")
        
        if [ -n "$LAYER_ARN" ]; then
            print_info "Lambda Layer created: $LAYER_ARN"
        else
            print_warning "Lambda Layer creation failed, will retry later"
        fi
        
        rm -rf "$LAYER_DIR" /tmp/requests-layer.zip
        
        # Create deployment package (without requests)
        cd "$PROJECT_ROOT/lambda/invoker"
        zip -r /tmp/phase6-lambda.zip . -x "*.pyc" "__pycache__/*" >/dev/null 2>&1
        
        # Update Lambda function with Layer and DNS-based BRIDGE_URL
        if [ -n "$LAYER_ARN" ]; then
            aws lambda update-function-code \
              --function-name sila2-agentcore-invoker \
              --zip-file fileb:///tmp/phase6-lambda.zip \
              --region $REGION >/dev/null 2>&1 || print_warning "Lambda code update skipped"
            
            aws lambda update-function-configuration \
              --function-name sila2-agentcore-invoker \
              --layers "$LAYER_ARN" \
              --environment "Variables={BRIDGE_URL=$BRIDGE_DNS}" \
              --region $REGION >/dev/null 2>&1 || print_warning "Lambda layer attachment skipped"
            
            print_info "Lambda Layer attached to function"
            print_info "Lambda BRIDGE_URL set to: $BRIDGE_DNS"
        else
            aws lambda update-function-code \
              --function-name sila2-agentcore-invoker \
              --zip-file fileb:///tmp/phase6-lambda.zip \
              --region $REGION >/dev/null 2>&1 || print_warning "Lambda update skipped (will update after AgentCore deployment)"
        fi
        
        # Cleanup
        rm /tmp/phase6-lambda.zip
        
        cd "$PROJECT_ROOT"
    fi
    
    print_success "Phase 6 infrastructure deployed"
    
    # Deploy EventBridge Scheduler
    print_step "Deploying EventBridge Scheduler"
    if [[ -f "$PROJECT_ROOT/infrastructure/eventbridge-scheduler.yaml" ]]; then
        LAMBDA_ARN=$(aws lambda get-function \
          --function-name sila2-agentcore-invoker \
          --region $REGION \
          --query 'Configuration.FunctionArn' \
          --output text 2>/dev/null)
        
        if [ -n "$LAMBDA_ARN" ]; then
            aws cloudformation deploy \
              --template-file "$PROJECT_ROOT/infrastructure/eventbridge-scheduler.yaml" \
              --stack-name sila2-eventbridge-scheduler \
              --parameter-overrides \
                LambdaFunctionArn=$LAMBDA_ARN \
                ScheduleInterval=5 \
              --region $REGION
            print_success "EventBridge Scheduler deployed (5 minute interval)"
        else
            print_warning "Lambda function not found, skipping EventBridge Scheduler"
        fi
    fi
else
    print_warning "Phase 6 CloudFormation not found, skipping"
fi

print_success "ECS + Lambda Proxy + Phase 6 deployed successfully"
print_info "Endpoint: $ENDPOINT"
print_info "Lambda: $LAMBDA_ARN"
print_info "Next: ./scripts/04_create_gateway.sh"
