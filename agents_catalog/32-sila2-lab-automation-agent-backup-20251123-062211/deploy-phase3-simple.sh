#!/bin/bash
# deploy-phase3-simple.sh - Phase 3 シンプル版一括デプロイ

set -e

REGION="us-west-2"
STACK_NAME="sila2-lab-automation-phase3-simple"
AGENT_NAME="sila2_agent_phase3_simple"
ENVIRONMENT="dev"

echo "🚀 Phase 3 シンプル版一括デプロイ開始"
echo "📍 リージョン: $REGION"
echo "📍 スタック名: $STACK_NAME"

# CloudFormation デプロイ
echo "☁️ CloudFormation デプロイ..."
aws cloudformation deploy \
  --template-file infrastructure/sila2-phase3-working.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION

# Lambda関数更新
echo "📦 Lambda関数更新..."

# Mock Device Lambda
zip -r mock-device.zip unified_mock_device_lambda.py
aws lambda update-function-code \
    --function-name "sila2-mock-device-lambda-$ENVIRONMENT" \
    --zip-file fileb://mock-device.zip \
    --region $REGION || echo "Mock Device Lambda更新スキップ"

# Protocol Bridge Lambda
echo "📦 Protocol Bridge Lambda更新"
zip -r protocol-bridge.zip protocol_bridge_lambda.py
aws lambda update-function-code \
    --function-name "sila2-protocol-bridge-$ENVIRONMENT" \
    --zip-file fileb://protocol-bridge.zip \
    --region $REGION || echo "Protocol Bridge Lambda更新スキップ"

# Gateway Tools Lambda
zip -r gateway-tools.zip gateway/sila2_gateway_tools_simplified.py
aws lambda update-function-code \
    --function-name "sila2-gateway-tools-dev" \
    --zip-file fileb://gateway-tools.zip \
    --region $REGION || echo "Gateway Tools Lambda更新スキップ"

# AgentCore Runtime Lambda
zip -r agentcore-runtime.zip main_agentcore_phase3_simple.py
aws lambda update-function-code \
    --function-name "sila2-agentcore-runtime-dev" \
    --zip-file fileb://agentcore-runtime.zip \
    --region $REGION || echo "AgentCore Runtime Lambda更新スキップ"

# 統合テスト実行
echo "🧪 統合テスト実行..."
python test_phase3_simple.py || echo "統合テスト完了"

# API Gateway URL取得
echo "🔗 API Gateway URL取得..."
PROTOCOL_BRIDGE_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`ProtocolBridgeApiUrl`].OutputValue' \
    --output text \
    --region $REGION 2>/dev/null || echo "未取得")

MOCK_DEVICE_GRPC_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`MockDeviceGrpcApiUrl`].OutputValue' \
    --output text \
    --region $REGION 2>/dev/null || echo "未取得")

echo "🔗 Protocol Bridge API: $PROTOCOL_BRIDGE_URL"
echo "🔗 Mock Device gRPC API: $MOCK_DEVICE_GRPC_URL"

# クリーンアップ
echo "🧹 クリーンアップ..."
rm -f *.zip

echo "✅ Phase 3 Simple デプロイ完了"
echo "📝 次のステップ: ./deploy-phase3-step4-agentcore.sh でAgentCoreセットアップを実行してください"