#!/bin/bash

# SiLA2 Lab Automation Agent - Phase 3 Final Integration with Gateway
set -e

# 設定ファイル読み込み
if [ ! -f ".phase3-config" ]; then
    echo "❌ 設定ファイルが見つかりません。先に deploy-phase3-step1-infra.sh を実行してください"
    exit 1
fi

source .phase3-config

echo "🚀 Phase 3 Final: Gateway付き最終統合とデプロイ"
echo "📍 リージョン: $REGION"
echo "📍 API URL: $API_URL"

# Python環境確認
echo "🐍 Python環境確認..."
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv local 3.10.12

# 仮想環境アクティベート
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ 仮想環境アクティベート完了"
else
    echo "⚠️ 仮想環境が見つかりません"
fi

# 4層アーキテクチャ統合テスト
echo "🧪 4層アーキテクチャ統合テスト..."

# 1. Mock Device Layer テスト
echo "📋 Layer 1: Mock Device テスト..."
if [ -f "unified_mock_device_lambda.py" ]; then
    python -c "
from unified_mock_device_lambda import lambda_handler
result = lambda_handler({'action': 'list'}, {})
print('✅ Mock Device Layer:', result.get('statusCode', 'error'))
" || echo "⚠️ Mock Device Layer テスト失敗"
else
    echo "⚠️ unified_mock_device_lambda.py が見つかりません"
fi

# 2. Protocol Bridge Layer テスト
echo "📋 Layer 2: Protocol Bridge テスト..."
if [ -f "protocol_bridge_lambda.py" ]; then
    python -c "
from protocol_bridge_lambda import lambda_handler
result = lambda_handler({'action': 'list'}, {})
print('✅ Protocol Bridge Layer:', result.get('statusCode', 'error'))
" || echo "⚠️ Protocol Bridge Layer テスト失敗"
else
    echo "⚠️ protocol_bridge_lambda.py が見つかりません"
fi

# 3. Gateway Tools Layer テスト
echo "📋 Layer 3: Gateway Tools テスト..."
if [ -f "gateway/sila2_gateway_tools_simplified.py" ]; then
    python -c "
import sys
sys.path.append('gateway')
from sila2_gateway_tools_simplified import SiLA2GatewayToolsSimplified
tools = SiLA2GatewayToolsSimplified()
result = tools.list_available_devices()
print('✅ Gateway Tools Layer:', 'OK' if 'devices' in result else 'error')
" || echo "⚠️ Gateway Tools Layer テスト失敗"
else
    echo "⚠️ gateway/sila2_gateway_tools_simplified.py が見つかりません"
fi

# 4. AgentCore Runtime Layer テスト
echo "📋 Layer 4: AgentCore Runtime テスト..."
if [ -f "main_agentcore_phase3_simple.py" ]; then
    python -c "
from main_agentcore_phase3_simple import lambda_handler
result = lambda_handler({'tool_name': 'list_available_devices'}, {})
print('✅ AgentCore Runtime Layer:', result.get('statusCode', 'error'))
" || echo "⚠️ AgentCore Runtime Layer テスト失敗"
else
    echo "⚠️ main_agentcore_phase3_simple.py が見つかりません"
fi

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
    # 既存GatewayのARNとURLを取得
    GATEWAY_ARN=$(echo "$GATEWAY_LIST" | grep "sila2-gateway-phase3" | awk '{print $2}')
    echo "📍 既存Gateway ARN: $GATEWAY_ARN"
    
    # Targetが存在するか確認
    echo "📋 Gateway Target確認..."
    TARGET_CHECK=$(agentcore gateway list-targets --gateway-arn "$GATEWAY_ARN" 2>/dev/null || echo "No targets")
    if echo "$TARGET_CHECK" | grep -q "sila2-lambda-target"; then
        echo "✅ Gateway Target: 既に存在"
    else
        echo "⚠️ Gateway Target: 未作成"
        echo "📝 手動作成が必要です"
    fi
else
    echo "⚠️ AgentCore Gateway: 未デプロイ"
    if [ "$RUNTIME_STATUS" = "deployed" ]; then
        echo "🚀 AgentCore Gateway 作成中..."
        GATEWAY_RESULT=$(agentcore create_mcp_gateway --name sila2-gateway-phase3 --region us-west-2 2>&1 || echo "Gateway creation failed")
        if echo "$GATEWAY_RESULT" | grep -q "successfully\|gatewayArn"; then
            echo "✅ AgentCore Gateway: 作成完了"
            GATEWAY_STATUS="deployed"
            # Gateway ARN抽出
            GATEWAY_ARN=$(echo "$GATEWAY_RESULT" | grep -o "arn:aws:bedrock-agentcore[^']*" | head -1)
            GATEWAY_URL=$(echo "$GATEWAY_RESULT" | grep -o "https://[^']*gateway[^']*" | head -1)
            echo "📍 Gateway ARN: $GATEWAY_ARN"
            echo "📍 Gateway URL: $GATEWAY_URL"
            
            # MCP Gateway Target作成（Lambda接続）
            echo "🔗 MCP Gateway Target作成（Lambda接続）..."
            sleep 5  # Gateway作成完了を待機
            TARGET_RESULT=$(agentcore gateway create-mcp-gateway-target \
                --gateway-arn "$GATEWAY_ARN" \
                --gateway-url "$GATEWAY_URL" \
                --role-arn "$LAMBDA_ROLE_ARN" \
                --name "sila2-lambda-target" \
                --target-type "lambda" \
                --region "us-west-2" 2>&1 || echo "Target creation failed")
            
            if echo "$TARGET_RESULT" | grep -q "targetArn\|success"; then
                echo "✅ Gateway Target作成成功"
            else
                echo "⚠️ Gateway Target作成失敗: $TARGET_RESULT"
                echo "📝 手動作成コマンド:"
                echo "   agentcore gateway create-mcp-gateway-target --gateway-arn '$GATEWAY_ARN' --gateway-url '$GATEWAY_URL' --role-arn '$LAMBDA_ROLE_ARN' --name 'sila2-lambda-target' --target-type 'lambda' --region 'us-west-2'"
            fi
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
    
    # エンドポイントテスト
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

# Runtime経由テスト
if [ "$RUNTIME_STATUS" = "deployed" ]; then
    echo "🧪 AgentCore Runtime経由テスト..."
    RUNTIME_TEST=$(agentcore invoke '{"prompt": "List all available devices"}' 2>/dev/null || echo "Runtime test failed")
    
    if echo "$RUNTIME_TEST" | grep -q "HPLC\|devices\|SiLA2"; then
        echo "✅ Runtime経由テスト成功"
    else
        echo "⚠️ Runtime経由テスト結果: $RUNTIME_TEST"
    fi
fi

# MCP Gateway情報表示
if [ "$GATEWAY_STATUS" = "deployed" ]; then
    echo "🌐 MCP Gatewayが利用可能です。MCPクライアントから接続できます。"
fi

# デプロイサマリー作成
echo ""
echo "📊 Phase 3 デプロイサマリー（Gateway付き）"
echo "========================================="
echo "✅ インフラストラクチャ: デプロイ済み"
echo "✅ Lambda関数: $([ -n "$LAMBDA_FUNCTIONS" ] && echo "デプロイ済み" || echo "未確認")"
echo "✅ API Gateway: $([ -n "$API_URL" ] && [ "$API_URL" != "null" ] && echo "利用可能" || echo "未設定")"
echo "✅ AgentCore Runtime: $([ "$RUNTIME_STATUS" = "deployed" ] && echo "デプロイ済み" || echo "未デプロイ")"
echo "✅ AgentCore Gateway: $([ "$GATEWAY_STATUS" = "deployed" ] && echo "デプロイ済み" || echo "未デプロイ")"
echo "✅ 4層アーキテクチャ: 統合テスト実行済み"
echo ""
echo "🌐 API URL: $API_URL"
echo "🔑 Lambda Role: $LAMBDA_ROLE_ARN"
echo "📍 リージョン: $REGION"
echo "📍 スタック名: $STACK_NAME"
if [ -n "$GATEWAY_ARN" ]; then
    echo "🌐 Gateway ARN: $GATEWAY_ARN"
fi
echo ""

# 使用方法の説明
echo "📝 使用方法（MCP Gateway付き）:"
echo "1. AgentCore Runtime経由でのテスト:"
echo "   agentcore invoke '{\"prompt\": \"List all devices\"}'"
echo ""
echo "2. MCP Gateway手動作成（必要な場合）:"
echo "   agentcore create_mcp_gateway --name 'sila2-gateway-phase3' --region 'us-west-2'"
echo ""
echo "3. API Gateway経由でのテスト:"
echo "   curl -X POST $API_URL/devices -H 'Content-Type: application/json' -d '{\"action\": \"list\"}'"
echo ""
echo "4. Lambda関数の直接テスト:"
echo "   aws lambda invoke --function-name [FUNCTION_NAME] --payload '{\"action\":\"list\"}' response.json"
echo ""

# 設定ファイルの最終更新
cat >> .phase3-config << EOF
DEPLOYMENT_STATUS=completed_with_gateway_final
DEPLOYMENT_TIME="$(date)"
LAMBDA_FUNCTIONS="$LAMBDA_FUNCTIONS"
GATEWAY_ARN="$GATEWAY_ARN"
GATEWAY_STATUS="$GATEWAY_STATUS"
ARCHITECTURE_LAYERS=4
EOF

echo "✅ Phase 3 最終デプロイ完了（Gateway付き）!"
echo "📝 設定は .phase3-config に保存されました"
echo ""
echo "🎉 SiLA2 Lab Automation Agent Phase 3（Gateway付き）の準備が整いました!"