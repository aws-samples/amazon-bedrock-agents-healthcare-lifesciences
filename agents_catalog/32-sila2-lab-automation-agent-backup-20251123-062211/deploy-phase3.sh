#!/bin/bash
# Phase 3 修正版デプロイスクリプト

set -e

echo "🚀 Phase 3 修正版デプロイ開始"

# Step 1: 修正されたインフラストラクチャをデプロイ
echo "📦 修正されたインフラストラクチャをデプロイ中..."
aws cloudformation deploy \
  --template-file infrastructure/sila2-phase3-working-fixed.yaml \
  --stack-name sila2-lab-automation-phase3-infra \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides Environment=dev

# Step 2: 修正されたAgentCore設定
echo "🤖 修正されたAgentCore設定を適用中..."
./deploy-phase3-step4-agentcore-fixed.sh

# Step 3: AgentCore Runtime再デプロイ
echo "🚀 AgentCore Runtime再デプロイ中..."
~/.pyenv/versions/3.10.*/bin/agentcore launch \
  --agent sila2_runtime_phase3 \
  --auto-update-on-conflict \
  --env API_GATEWAY_URL=https://n6ky0ru9nd.execute-api.us-west-2.amazonaws.com/dev \
  --env ENVIRONMENT=dev \
  --env PHASE=3

# Step 4: 動作確認
echo "✅ 動作確認中..."
~/.pyenv/versions/3.10.*/bin/agentcore invoke "List all devices"

echo "🎉 Phase 3 修正版デプロイ完了"