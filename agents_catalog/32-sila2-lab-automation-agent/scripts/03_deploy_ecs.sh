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

print_success "ECS + Lambda Proxy deployed successfully"
print_info "Endpoint: $ENDPOINT"
print_info "Lambda: $LAMBDA_ARN"
print_info "Next: ./scripts/04_create_gateway.sh"
