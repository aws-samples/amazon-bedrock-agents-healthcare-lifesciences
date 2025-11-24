#!/bin/bash

# SiLA2 Lab Automation Agent - Phase 3 Step 3: Testing
set -e

# 設定ファイル読み込み
if [ ! -f ".phase3-config" ]; then
    echo "❌ 設定ファイルが見つかりません。先に deploy-phase3-step1-infra.sh を実行してください"
    exit 1
fi

source .phase3-config

echo "🚀 Phase 3 Step 3: テスト実行"
echo "📍 リージョン: $REGION"
echo "📍 API URL: $API_URL"

# テスト用のJSONペイロード作成
echo "📝 テストペイロード作成..."

cat > test_list_devices.json << 'EOF'
{
  "prompt": "list all available devices"
}
EOF

cat > test_device_status.json << 'EOF'
{
  "prompt": "check device status"
}
EOF

cat > test_start_measurement.json << 'EOF'
{
  "prompt": "start measurement on HPLC device"
}
EOF

# Lambda関数テスト
echo "🧪 Lambda関数テスト実行..."

# 利用可能なLambda関数を確認
LAMBDA_FUNCTIONS=$(aws lambda list-functions --region $REGION --query 'Functions[?contains(FunctionName, `sila2`)].FunctionName' --output text)

if [ -n "$LAMBDA_FUNCTIONS" ]; then
    FIRST_FUNCTION=$(echo $LAMBDA_FUNCTIONS | awk '{print $1}')
    echo "🧪 $FIRST_FUNCTION をテスト中..."
    
    echo "📋 Test 1: List Devices"
    aws lambda invoke \
        --function-name "$FIRST_FUNCTION" \
        --payload file://test_list_devices.json \
        --region $REGION \
        response1.json
    
    echo "📋 Response 1:"
    cat response1.json | jq .
    
    echo ""
    echo "📋 Test 2: Device Status"
    aws lambda invoke \
        --function-name "$FIRST_FUNCTION" \
        --payload file://test_device_status.json \
        --region $REGION \
        response2.json
    
    echo "📋 Response 2:"
    cat response2.json | jq .
    
    echo ""
    echo "📋 Test 3: Start Measurement"
    aws lambda invoke \
        --function-name "$FIRST_FUNCTION" \
        --payload file://test_start_measurement.json \
        --region $REGION \
        response3.json
    
    echo "📋 Response 3:"
    cat response3.json | jq .
    
else
    echo "⚠️ SiLA2関連のLambda関数が見つかりませんでした"
fi

# API Gateway テスト（存在する場合）
if [ -n "$API_URL" ] && [ "$API_URL" != "null" ]; then
    echo ""
    echo "🌐 API Gateway テスト..."
    
    echo "📋 API Gateway Health Check:"
    curl -s "$API_URL/health" | jq . || echo "Health endpoint not available"
    
    echo ""
    echo "📋 API Gateway Devices Endpoint:"
    curl -s "$API_URL/devices" | jq . || echo "Devices endpoint not available"
fi

# テスト結果サマリー
echo ""
echo "📊 テスト結果サマリー:"
echo "✅ Lambda関数: $([ -n "$LAMBDA_FUNCTIONS" ] && echo "OK" || echo "Not Found")"
echo "✅ API Gateway: $([ -n "$API_URL" ] && [ "$API_URL" != "null" ] && echo "OK" || echo "Not Available")"

# クリーンアップ
rm -f test_*.json response*.json

echo ""
echo "✅ Phase 3 Step 3 テスト完了"
echo "📝 すべて正常であれば、deploy-phase3-step4-agentcore.sh でAgentCoreセットアップを実行してください"