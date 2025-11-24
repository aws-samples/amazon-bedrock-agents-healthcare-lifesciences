#!/bin/bash
# AgentCore Runtime デバッグスクリプト

set -e

# 設定読み込み
source .phase3-config

echo "🔍 AgentCore Runtime デバッグ開始"
echo "Region: $REGION"

# CloudWatchログ確認
echo "📋 CloudWatchログ確認中..."

# AgentCore Runtime関連のログストリーム取得
LOG_GROUP="/aws/lambda/sila2-agentcore-runtime-dev"

echo "ロググループ: $LOG_GROUP"

# 最新のログストリーム取得
LATEST_STREAM=$(aws logs describe-log-streams \
    --log-group-name "$LOG_GROUP" \
    --order-by LastEventTime \
    --descending \
    --max-items 1 \
    --region $REGION \
    --query 'logStreams[0].logStreamName' \
    --output text 2>/dev/null || echo "")

if [ "$LATEST_STREAM" != "" ] && [ "$LATEST_STREAM" != "None" ]; then
    echo "最新ログストリーム: $LATEST_STREAM"
    echo ""
    echo "🔍 最新ログ内容:"
    aws logs get-log-events \
        --log-group-name "$LOG_GROUP" \
        --log-stream-name "$LATEST_STREAM" \
        --region $REGION \
        --query 'events[*].[timestamp,message]' \
        --output table
else
    echo "❌ ログストリームが見つかりません"
fi

echo ""
echo "📊 Lambda関数設定確認:"

# Lambda関数設定確認
aws lambda get-function-configuration \
    --function-name "sila2-agentcore-runtime-dev" \
    --region $REGION \
    --query '{
        Runtime: Runtime,
        Handler: Handler,
        Timeout: Timeout,
        MemorySize: MemorySize,
        Environment: Environment,
        State: State,
        LastUpdateStatus: LastUpdateStatus
    }' \
    --output table

echo ""
echo "🐳 ECRイメージ確認:"

# ECRリポジトリ確認
aws ecr describe-images \
    --repository-name "bedrock-agentcore-sila2_runtime_phase3_simple" \
    --region us-west-2 \
    --query 'imageDetails[0].{
        ImageTags: imageTags,
        ImagePushedAt: imagePushedAt,
        ImageSizeInBytes: imageSizeInBytes
    }' \
    --output table 2>/dev/null || echo "ECRイメージ情報取得エラー"

echo ""
echo "🧪 簡単なテスト実行:"

# 簡単なテストペイロード作成
cat > simple_test.json << EOF
{
  "tool_name": "list_available_devices",
  "parameters": {}
}
EOF

# Lambda関数直接テスト
echo "Lambda関数直接テスト実行中..."
aws lambda invoke \
    --function-name "sila2-agentcore-runtime-dev" \
    --payload file://simple_test.json \
    --region $REGION \
    simple_test_result.json 2>&1 || echo "Lambda直接実行エラー"

if [ -f simple_test_result.json ]; then
    echo "テスト結果:"
    cat simple_test_result.json | jq . 2>/dev/null || cat simple_test_result.json
fi

# クリーンアップ
rm -f simple_test.json simple_test_result.json

echo ""
echo "🔧 修復提案:"
echo "1. CloudWatchログでエラー詳細を確認"
echo "2. Lambda関数のRuntime設定確認"
echo "3. ECRイメージの再ビルド・プッシュ"
echo "4. 環境変数設定確認"