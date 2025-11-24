#!/bin/bash
# AgentCore Runtime再作成スクリプト

set -e

# 設定読み込み
source .phase3-config

echo "🔄 AgentCore Runtime再作成開始"
echo "Region: $REGION"

# 既存のAgentCore Runtime削除
echo "🗑️ 既存のAgentCore Runtime削除中..."
agentcore runtime delete sila2_runtime_phase3_simple --force || echo "削除対象が見つかりません"

# 少し待機
sleep 5

# 新しいAgentCore Runtime作成
echo "🚀 新しいAgentCore Runtime作成中..."

# runtime.yamlを修正
cat > runtime.yaml << EOF
name: sila2_runtime_phase3_simple
description: "SiLA2 Lab Automation Agent Runtime - Phase 3 Simple"
model: anthropic.claude-3-5-sonnet-20241022-v2:0
system_prompt: |
  あなたはSiLA2ラボ自動化システムの専門エージェントです。
  
  利用可能なツール:
  - list_available_devices: 利用可能なSiLA2デバイス一覧を取得
  - get_device_status: 指定デバイスのステータス確認
  - execute_device_command: デバイスコマンド実行
  
  ユーザーの要求に応じて適切なツールを使用し、SiLA2デバイスの操作を支援してください。
  日本語で応答してください。

tools:
  - name: list_available_devices
    description: "利用可能なSiLA2デバイス一覧を取得します"
    lambda_function: sila2-agentcore-runtime-dev
    parameters:
      type: object
      properties: {}
      required: []

  - name: get_device_status
    description: "指定されたSiLA2デバイスのステータスを取得します"
    lambda_function: sila2-agentcore-runtime-dev
    parameters:
      type: object
      properties:
        device_id:
          type: string
          description: "ステータスを確認するデバイスID"
      required: ["device_id"]

  - name: execute_device_command
    description: "指定されたSiLA2デバイスでコマンドを実行します"
    lambda_function: sila2-agentcore-runtime-dev
    parameters:
      type: object
      properties:
        device_id:
          type: string
          description: "コマンドを実行するデバイスID"
        command:
          type: string
          description: "実行するコマンド"
      required: ["device_id", "command"]

runtime_config:
  timeout: 300
  memory: 512
  environment:
    API_GATEWAY_URL: $API_URL
EOF

# AgentCore Runtime作成
agentcore runtime create runtime.yaml

echo "✅ AgentCore Runtime作成完了"

# 少し待機してからテスト
echo "⏳ Runtime初期化待機中..."
sleep 10

# テスト実行
echo "🧪 新しいRuntime テスト実行中..."

# テスト用ペイロード作成
cat > test_new_runtime.json << EOF
{
  "message": "利用可能なSiLA2デバイスを教えてください"
}
EOF

# AgentCore invoke実行
echo "📋 デバイス一覧取得テスト:"
agentcore invoke test_new_runtime.json || echo "テスト実行エラー"

# クリーンアップ
rm -f test_new_runtime.json

echo ""
echo "✅ AgentCore Runtime再作成完了"
echo ""
echo "🎯 次のステップ: 正常に動作することを確認してください"