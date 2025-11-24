#!/bin/bash
# deploy-phase3-fixed.sh - 修正版デプロイスクリプト

set -e

REGION="us-west-2"
STACK_NAME="sila2-lab-automation-phase3-fixed"
ACCOUNT_ID="590183741681"

echo "🚀 Phase 3 修正版デプロイ開始"

# Step 1: CloudFormation デプロイ
echo "📦 Step 1: CloudFormation デプロイ"
aws cloudformation deploy \
  --template-file infrastructure/sila2-phase3-working.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION

# Step 2: Lambda関数更新（urllib版）
echo "🔧 Step 2: Lambda関数更新"

# Mock Device Lambda
zip -r mock-device.zip unified_mock_device_lambda.py
aws lambda update-function-code \
    --function-name "sila2-mock-device-lambda-dev" \
    --zip-file fileb://mock-device.zip \
    --region $REGION

# Protocol Bridge Lambda（urllib版に修正）
cp protocol_bridge_lambda.py protocol_bridge_lambda_urllib.py
sed -i 's/import requests/import urllib.request\nimport urllib.parse/g' protocol_bridge_lambda_urllib.py
zip -r protocol-bridge.zip protocol_bridge_lambda_urllib.py
aws lambda update-function-code \
    --function-name "sila2-protocol-bridge-dev" \
    --zip-file fileb://protocol-bridge.zip \
    --region $REGION

# AgentCore Runtime Lambda（正しいファイル名）
cp main_agentcore_phase3_simple.py agentcore_runtime_sila2.py
zip -r agentcore-runtime.zip agentcore_runtime_sila2.py
aws lambda update-function-code \
    --function-name "sila2-agentcore-runtime-dev" \
    --zip-file fileb://agentcore-runtime.zip \
    --region $REGION

# Step 3: ECRイメージ更新
echo "🐳 Step 3: ECRイメージ更新"
docker build -t sila2-agentcore-runtime-dev .
docker tag sila2-agentcore-runtime-dev:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bedrock-agentcore-sila2_runtime_phase3_simple:latest
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bedrock-agentcore-sila2_runtime_phase3_simple:latest

# Step 4: MCP Gateway作成
echo "🌐 Step 4: MCP Gateway作成"
GATEWAY_ARN=$(aws bedrock-agentcore create-gateway \
    --name "sila2-gateway-fixed" \
    --region $REGION \
    --query 'gatewayArn' --output text)

# Step 5: Gateway Target作成
echo "🎯 Step 5: Gateway Target作成"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)

aws bedrock-agentcore create-gateway-target \
    --gateway-arn $GATEWAY_ARN \
    --name "sila2-lambda-target" \
    --target-type "LAMBDA" \
    --target-config "{\"lambdaConfig\":{\"functionArn\":\"arn:aws:lambda:$REGION:$ACCOUNT_ID:function:sila2-agentcore-runtime-dev\"}}" \
    --region $REGION

# Step 6: 設定保存
echo "💾 Step 6: 設定保存"
cat > .phase3-fixed-config << EOF
API_URL="$API_URL"
GATEWAY_ARN="$GATEWAY_ARN"
STACK_NAME="$STACK_NAME"
DEPLOYMENT_STATUS=completed_fixed
DEPLOYMENT_TIME="$(date)"
ARCHITECTURE_LAYERS=4
EOF

echo "✅ Phase 3 修正版デプロイ完了"
echo "🔗 API Gateway URL: $API_URL"
echo "🌐 Gateway ARN: $GATEWAY_ARN"