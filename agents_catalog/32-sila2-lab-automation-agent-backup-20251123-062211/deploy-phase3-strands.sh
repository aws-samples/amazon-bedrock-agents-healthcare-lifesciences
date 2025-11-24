#!/bin/bash
# Phase 3: Strands Agent + AgentCore Gateway デプロイ

set -e

source .phase3-config

echo "🚀 Phase 3: Strands Agent + AgentCore Gateway デプロイ開始"
echo "API URL: $API_URL"
echo "Region: $REGION"

# 1. AgentCore Gateway作成
echo "🌉 AgentCore Gateway作成中..."
agentcore create_mcp_gateway \
    --name "sila2_gateway" \
    --description "SiLA2 Lab Automation Gateway"

# 2. Lambda関数をGateway Targetとして登録
echo "🎯 Gateway Target登録中..."
agentcore create_mcp_gateway_target \
    --gateway-name "sila2_gateway" \
    --target-name "list_available_devices" \
    --lambda-function "sila2-agentcore-runtime-dev" \
    --description "利用可能なSiLA2デバイス一覧を取得"

agentcore create_mcp_gateway_target \
    --gateway-name "sila2_gateway" \
    --target-name "get_device_status" \
    --lambda-function "sila2-agentcore-runtime-dev" \
    --description "指定デバイスのステータス取得"

agentcore create_mcp_gateway_target \
    --gateway-name "sila2_gateway" \
    --target-name "execute_device_command" \
    --lambda-function "sila2-agentcore-runtime-dev" \
    --description "デバイスコマンド実行"

# 3. Strands Agent設定
echo "🤖 Strands Agent設定中..."
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
pyenv local 3.10.12

# Strands Agent起動
python -c "
from strands_agent import agent
agent.run_with_agentcore_gateway('sila2_gateway')
"

echo "✅ Strands Agent + AgentCore Gateway デプロイ完了"
echo ""
echo "🧪 テスト実行:"
echo "agentcore invoke '{\"message\": \"利用可能なデバイスを教えてください\"}'"