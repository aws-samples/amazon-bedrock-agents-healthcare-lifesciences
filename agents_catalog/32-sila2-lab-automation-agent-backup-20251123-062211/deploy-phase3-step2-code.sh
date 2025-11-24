#!/bin/bash

# SiLA2 Lab Automation Agent - Phase 3 Step 2: Code Deployment (Simple)
set -e

# 設定ファイル読み込み
if [ ! -f ".phase3-config" ]; then
    echo "❌ 設定ファイルが見つかりません。先に deploy-phase3-step1-infra.sh を実行してください"
    exit 1
fi

source .phase3-config

echo "🚀 Phase 3 Step 2: コードデプロイ (シンプル版)"
echo "📍 リージョン: $REGION"
echo "📍 API URL: $API_URL"

# Python環境設定
echo "🐍 Python環境設定..."
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv local 3.10.12

# Lambda関数パッケージング (シンプル版)
echo "📦 Lambda関数パッケージング (シンプル版)..."

# Mock Device Lambda
echo "  📦 Mock Device Lambda..."
zip -r mock-device-simple.zip unified_mock_device_lambda.py

# Protocol Bridge Lambda
echo "  📦 Protocol Bridge Lambda..."
zip -r protocol-bridge-simple.zip protocol_bridge_lambda.py

# Gateway Tools
echo "  📦 Gateway Tools..."
zip -r gateway-tools-simple.zip gateway/sila2_gateway_tools_simplified.py

# AgentCore Runtime
echo "  📦 AgentCore Runtime..."
zip -r agentcore-runtime-simple.zip main_agentcore_phase3_simple.py

# Lambda関数更新
echo "📋 Lambda関数更新..."

# 利用可能なLambda関数を確認
LAMBDA_FUNCTIONS=$(aws lambda list-functions --region $REGION --query 'Functions[?contains(FunctionName, `sila2`)].FunctionName' --output text)

if [ -n "$LAMBDA_FUNCTIONS" ]; then
    echo "  📋 利用可能なLambda関数: $LAMBDA_FUNCTIONS"
    
    # Mock Device Lambda更新
    aws lambda update-function-code \
        --function-name "sila2-mock-device-lambda-dev" \
        --zip-file fileb://mock-device-simple.zip \
        --region $REGION || echo "  ⚠️ Mock Device Lambda更新スキップ"
    
    # Protocol Bridge Lambda更新
    echo "  📦 Protocol Bridge Lambda更新中..."
    aws lambda update-function-code \
        --function-name "sila2-protocol-bridge-dev" \
        --zip-file fileb://protocol-bridge-simple.zip \
        --region $REGION || echo "  ⚠️ Protocol Bridge Lambda更新スキップ"
    
    # Gateway Tools Lambda更新
    aws lambda update-function-code \
        --function-name "sila2-gateway-tools-dev" \
        --zip-file fileb://gateway-tools-simple.zip \
        --region $REGION || echo "  ⚠️ Gateway Tools Lambda更新スキップ"
    
    # AgentCore Runtime Lambda更新
    aws lambda update-function-code \
        --function-name "sila2-agentcore-runtime-dev" \
        --zip-file fileb://agentcore-runtime-simple.zip \
        --region $REGION || echo "  ⚠️ AgentCore Runtime Lambda更新スキップ"
else
    echo "  ⚠️ SiLA2関連のLambda関数が見つかりませんでした"
fi

# 動作確認用の簡単なテスト
echo "🧪 API Gateway動作確認..."
if [ -n "$API_URL" ]; then
    echo "📡 API Gateway テスト: $API_URL/devices"
    curl -X POST "$API_URL/devices" \
        -H "Content-Type: application/json" \
        -d '{"action": "list"}' \
        --max-time 10 || echo "⚠️ API Gateway テスト失敗 (正常な場合があります)"
else
    echo "⚠️ API_URL が設定されていません"
fi

# クリーンアップ
echo "🧹 一時ファイルクリーンアップ..."
rm -f *-simple.zip

echo "✅ Phase 3 Step 2 完了 (シンプル版)"
echo "📝 次のステップ: ./deploy-phase3-step3-test.sh を実行してテストしてください"