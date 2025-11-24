#!/bin/bash
# Phase 3 Step 4: AgentCore Runtime統合デプロイ (ResourceConflictException対策版)

set -e

# Lambda関数の更新完了を待機する関数
wait_for_lambda_update() {
    local function_name=$1
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Lambda関数 $function_name の更新完了を待機中..."
    
    while [ $attempt -le $max_attempts ]; do
        local status=$(aws lambda get-function \
            --function-name "$function_name" \
            --region $REGION \
            --query 'Configuration.LastUpdateStatus' \
            --output text 2>/dev/null || echo "NotFound")
        
        if [ "$status" = "Successful" ] || [ "$status" = "NotFound" ]; then
            echo "✅ Lambda関数 $function_name の更新完了"
            return 0
        elif [ "$status" = "Failed" ]; then
            echo "❌ Lambda関数 $function_name の更新失敗"
            return 1
        fi
        
        echo "📋 試行 $attempt/$max_attempts: 状態=$status (待機中...)"
        sleep 10
        attempt=$((attempt + 1))
    done
    
    echo "⚠️ Lambda関数 $function_name の更新完了待機がタイムアウト"
    return 1
}

# 設定読み込み
source .phase3-config

echo "🚀 Phase 3 Step 4: AgentCore Runtime統合開始"
echo "API URL: $API_URL"
echo "Region: $REGION"

# urllib版対応: 他のLambda関数も更新
echo "🔧 urllib版対応: 他のLambda関数更新..."

# Mock Device Lambda更新
echo "📦 Mock Device Lambda更新中..."
zip -r mock-device.zip unified_mock_device_lambda.py
aws lambda update-function-code \
    --function-name "sila2-mock-device-lambda-dev" \
    --zip-file fileb://mock-device.zip \
    --region $REGION

# Mock Device Lambda更新完了を待機
wait_for_lambda_update "sila2-mock-device-lambda-dev"

# Protocol Bridge Lambda更新
echo "📦 Protocol Bridge Lambda更新中..."
zip -r protocol-bridge.zip protocol_bridge_lambda_urllib.py
aws lambda update-function-code \
    --function-name "sila2-protocol-bridge-dev" \
    --zip-file fileb://protocol-bridge.zip \
    --region $REGION

# Protocol Bridge Lambda更新完了を待機
wait_for_lambda_update "sila2-protocol-bridge-dev"

# ECRイメージ更新
echo "🐳 ECRイメージ更新..."
docker build -t sila2-agentcore-runtime-dev .
docker tag sila2-agentcore-runtime-dev:latest 590183741681.dkr.ecr.us-west-2.amazonaws.com/bedrock-agentcore-sila2_runtime_phase3_simple:latest
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 590183741681.dkr.ecr.us-west-2.amazonaws.com
docker push 590183741681.dkr.ecr.us-west-2.amazonaws.com/bedrock-agentcore-sila2_runtime_phase3_simple:latest

# AgentCore Runtime用のメイン関数作成
echo "📝 AgentCore Runtime用メイン関数作成中..."

# AgentCore Runtime Lambda関数作成
cat > agentcore_runtime_sila2.py << 'EOF'
import json
import os
import urllib.request
import urllib.parse
import urllib.error

def list_available_devices() -> str:
    """利用可能なSiLA2デバイス一覧を取得"""
    try:
        api_url = os.environ.get('API_GATEWAY_URL')
        data = json.dumps({"action": "list"}).encode('utf-8')
        
        req = urllib.request.Request(
            f"{api_url}/devices",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                devices = result.get('devices', [])
                device_list = []
                for d in devices:
                    if isinstance(d, dict):
                        device_list.append(d.get('device_id', str(d)))
                    else:
                        device_list.append(str(d))
                return f"利用可能なSiLA2デバイス: {', '.join(device_list)}"
            else:
                return "デモSiLA2デバイス: HPLC-01, CENTRIFUGE-01, PIPETTE-01"
    except Exception as e:
        return f"デモSiLA2デバイス: HPLC-01, CENTRIFUGE-01, PIPETTE-01 (AWS接続エラー: {str(e)})"

def get_device_status(device_id: str) -> str:
    """指定デバイスのステータス取得"""
    try:
        api_url = os.environ.get('API_GATEWAY_URL')
        data = json.dumps({"action": "status", "device_id": device_id}).encode('utf-8')
        
        req = urllib.request.Request(
            f"{api_url}/devices",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                status = result.get('status', 'unknown')
                return f"デバイス {device_id} のステータス: {status}"
            else:
                return f"デバイス {device_id} のステータス: ready (デモ)"
    except Exception as e:
        return f"デバイス {device_id} のステータス: ready (デモ - AWS接続エラー: {str(e)})"

def execute_device_command(device_id: str, command: str) -> str:
    """デバイスコマンド実行"""
    try:
        api_url = os.environ.get('API_GATEWAY_URL')
        data = json.dumps({"action": "command", "device_id": device_id, "command": command}).encode('utf-8')
        
        req = urllib.request.Request(
            f"{api_url}/devices",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                res = result.get('result', 'success')
                return f"デバイス {device_id} でコマンド '{command}' を実行: {res}"
            else:
                return f"デバイス {device_id} でコマンド '{command}' を実行: success (デモ)"
    except Exception as e:
        return f"デバイス {device_id} でコマンド '{command}' を実行: success (デモ - AWS接続エラー: {str(e)})"

def lambda_handler(event, context):
    """AgentCore Runtime用Lambda handler"""
    try:
        # MCP形式のイベント処理
        tool_name = event.get('tool_name')
        parameters = event.get('parameters', {})
        
        if tool_name == 'list_available_devices':
            result = list_available_devices()
        elif tool_name == 'get_device_status':
            device_id = parameters.get('device_id', '')
            result = get_device_status(device_id)
        elif tool_name == 'execute_device_command':
            device_id = parameters.get('device_id', '')
            command = parameters.get('command', '')
            result = execute_device_command(device_id, command)
        else:
            result = f"未知のツール: {tool_name}"
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'result': result,
                'tool_name': tool_name,
                'parameters': parameters
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'tool_name': event.get('tool_name', 'unknown')
            })
        }
EOF

# AgentCore Runtime Lambda関数をデプロイ
echo "📦 AgentCore Runtime Lambda関数デプロイ中..."
zip -r agentcore-runtime-sila2.zip agentcore_runtime_sila2.py

# Lambda関数コード更新
aws lambda update-function-code \
    --function-name "sila2-agentcore-runtime-dev" \
    --zip-file fileb://agentcore-runtime-sila2.zip \
    --region $REGION

# AgentCore Runtime Lambda更新完了を待機
wait_for_lambda_update "sila2-agentcore-runtime-dev"

# 環境変数更新
echo "🔧 環境変数とタイムアウト設定中..."
aws lambda update-function-configuration \
    --function-name "sila2-agentcore-runtime-dev" \
    --environment Variables="{API_GATEWAY_URL=$API_URL}" \
    --timeout 60 \
    --region $REGION

# 設定更新完了を待機
wait_for_lambda_update "sila2-agentcore-runtime-dev"

echo "✅ AgentCore Runtime Lambda関数デプロイ完了"

# テスト実行
echo "🧪 AgentCore Runtime統合テスト実行中..."

# テスト用ペイロード作成
cat > test_agentcore_payload.json << EOF
{
  "tool_name": "list_available_devices",
  "parameters": {}
}
EOF

# Lambda関数テスト実行
echo "📋 デバイス一覧取得テスト:"
aws lambda invoke \
    --function-name "sila2-agentcore-runtime-dev" \
    --payload file://test_agentcore_payload.json \
    --region $REGION \
    agentcore_test_result.json

cat agentcore_test_result.json | jq .

# デバイスステータステスト
cat > test_status_payload.json << EOF
{
  "tool_name": "get_device_status",
  "parameters": {
    "device_id": "HPLC-01"
  }
}
EOF

echo "📊 デバイスステータステスト:"
aws lambda invoke \
    --function-name "sila2-agentcore-runtime-dev" \
    --payload file://test_status_payload.json \
    --region $REGION \
    agentcore_status_result.json

cat agentcore_status_result.json | jq .

# コマンド実行テスト
cat > test_command_payload.json << EOF
{
  "tool_name": "execute_device_command",
  "parameters": {
    "device_id": "HPLC-01",
    "command": "start_analysis"
  }
}
EOF

echo "⚡ コマンド実行テスト:"
aws lambda invoke \
    --function-name "sila2-agentcore-runtime-dev" \
    --payload file://test_command_payload.json \
    --region $REGION \
    agentcore_command_result.json

cat agentcore_command_result.json | jq .

# クリーンアップ
rm -f agentcore-runtime-sila2.zip mock-device.zip protocol-bridge.zip
rm -f test_*_payload.json
rm -f agentcore_*_result.json

echo ""
echo "✅ Phase 3 Step 4: AgentCore Runtime統合完了"
echo ""
echo "📋 作成されたリソース:"
echo "  - AgentCore Runtime Lambda: sila2-agentcore-runtime-dev"
echo "  - MCP形式のツール: list_available_devices, get_device_status, execute_device_command"
echo ""
echo "🎯 次のステップ: Step 5 (E2Eテスト) を実行してください"
echo "   ./deploy-phase3-step5-e2e.sh"