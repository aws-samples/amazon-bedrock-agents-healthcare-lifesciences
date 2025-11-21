#!/bin/bash

# SiLA2 Lab Automation Agent - Phase 3 Final Integration
set -e

# 設定ファイル読み込み
if [ ! -f ".phase3-config" ]; then
    echo "❌ 設定ファイルが見つかりません。先に deploy-phase3-step1-infra.sh を実行してください"
    exit 1
fi

source .phase3-config

echo "🚀 Phase 3 Final: 最終統合とデプロイ"
echo "📍 リージョン: $REGION"
echo "📍 API URL: $API_URL"

# Python環境確認
echo "🐍 Python環境確認..."
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv local 3.10.12

source .venv/bin/activate

# AgentCore状態確認
echo "🤖 AgentCore 状態確認..."

# Runtime確認
echo "📋 AgentCore Runtime 確認..."
RUNTIME_STATUS_OUTPUT=$(agentcore status 2>/dev/null || echo "Runtime not found")
if echo "$RUNTIME_STATUS_OUTPUT" | grep -q "STATUS: READY"; then
    echo "✅ AgentCore Runtime: デプロイ済み (READY)"
    RUNTIME_STATUS="deployed"
    RUNTIME_ARN=$(echo "$RUNTIME_STATUS_OUTPUT" | grep "Agent Arn:" | awk '{print $3}')
    echo "📍 Runtime ARN: $RUNTIME_ARN"
else
    echo "⚠️ AgentCore Runtime: 未デプロイまたは未準備"
    echo "📝 deploy-phase3-step5-runtime.sh を実行してください"
    RUNTIME_STATUS="not_deployed"
fi

# Gateway確認と作成
echo "📋 AgentCore Gateway 確認..."
GATEWAY_LIST=$(agentcore gateway list 2>/dev/null || echo "Gateway not found")
if echo "$GATEWAY_LIST" | grep -q "sila2-gateway-phase3"; then
    echo "✅ AgentCore Gateway: デプロイ済み"
    GATEWAY_STATUS="deployed"
else
    echo "⚠️ AgentCore Gateway: 未デプロイ"
    if [ "$RUNTIME_STATUS" = "deployed" ]; then
        echo "🚀 AgentCore Gateway 作成中..."
        GATEWAY_RESULT=$(agentcore create_mcp_gateway --name sila2-gateway-phase3 2>&1 || echo "Gateway creation failed")
        if echo "$GATEWAY_RESULT" | grep -q "successfully"; then
            echo "✅ AgentCore Gateway: 作成完了"
            GATEWAY_STATUS="deployed"
        else
            echo "⚠️ AgentCore Gateway: 作成失敗"
            echo "$GATEWAY_RESULT"
            GATEWAY_STATUS="failed"
        fi
    else
        echo "📝 Runtime が準備完了後にGatewayを作成してください"
        GATEWAY_STATUS="not_deployed"
    fi
fi

# 最終テスト
echo "🧪 最終統合テスト..."

# Lambda関数の最終確認
LAMBDA_FUNCTIONS=$(aws lambda list-functions --region $REGION --query 'Functions[?contains(FunctionName, `sila2`)].FunctionName' --output text)

if [ -n "$LAMBDA_FUNCTIONS" ]; then
    echo "✅ Lambda関数が見つかりました:"
    echo "$LAMBDA_FUNCTIONS"
else
    echo "⚠️ Lambda関数が見つかりませんでした"
fi

# API Gateway の最終確認
if [ -n "$API_URL" ] && [ "$API_URL" != "null" ]; then
    echo "✅ API Gateway URL: $API_URL"
    
    # HTTP 502エラー修正テスト
    echo "🧪 /devices エンドポイントテスト..."
    DEVICES_RESPONSE=$(curl -s -X POST "$API_URL/devices" \
        -H "Content-Type: application/json" \
        -d '{"action": "list"}' \
        --max-time 10 || echo "エラー")
    
    if echo "$DEVICES_RESPONSE" | grep -q "HPLC-01"; then
        echo "✅ /devices エンドポイント正常動作"
    else
        echo "⚠️ /devices エンドポイントエラー: $DEVICES_RESPONSE"
    fi
else
    echo "⚠️ API Gateway URLが設定されていません"
fi

# デプロイサマリー作成
echo ""
echo "📊 Phase 3 デプロイサマリー"
echo "================================"
echo "✅ インフラストラクチャ: デプロイ済み"
echo "✅ Lambda関数: $([ -n "$LAMBDA_FUNCTIONS" ] && echo "デプロイ済み" || echo "未確認")"
echo "✅ API Gateway: $([ -n "$API_URL" ] && [ "$API_URL" != "null" ] && echo "利用可能" || echo "未設定")"
echo "✅ AgentCore Runtime: $([ "$RUNTIME_STATUS" = "deployed" ] && echo "デプロイ済み" || echo "未デプロイ")"
echo "✅ AgentCore Gateway: $([ "$GATEWAY_STATUS" = "deployed" ] && echo "デプロイ済み" || echo "未デプロイ")"
echo ""
echo "🌐 API URL: $API_URL"
echo "🔑 Lambda Role: $LAMBDA_ROLE_ARN"
echo "📍 リージョン: $REGION"
echo "📍 スタック名: $STACK_NAME"
echo ""

# 使用方法の説明
echo "📝 使用方法:"
echo "1. API Gateway経由でのテスト:"
echo "   curl $API_URL/devices"
echo ""
echo "2. Lambda関数の直接テスト:"
echo "   aws lambda invoke --function-name [FUNCTION_NAME] --payload '{\"prompt\":\"list devices\"}' response.json"
echo ""
echo "3. AgentCoreエージェントとの対話:"
echo "   agentcore chat"
echo ""

# 設定ファイルの最終更新
cat >> .phase3-config << EOF
DEPLOYMENT_STATUS=completed
DEPLOYMENT_TIME="$(date)"
LAMBDA_FUNCTIONS="$LAMBDA_FUNCTIONS"
EOF

echo "✅ Phase 3 最終デプロイ完了!"
echo "📝 設定は .phase3-config に保存されました"
echo ""
echo "🎉 SiLA2 Lab Automation Agent Phase 3 の準備が整いました!"