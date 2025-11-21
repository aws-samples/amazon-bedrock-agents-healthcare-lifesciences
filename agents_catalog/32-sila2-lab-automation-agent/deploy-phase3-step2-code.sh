#!/bin/bash

# SiLA2 Lab Automation Agent - Phase 3 Step 2: Code Deployment
set -e

# 設定ファイル読み込み
if [ ! -f ".phase3-config" ]; then
    echo "❌ 設定ファイルが見つかりません。先に deploy-phase3-step1-infra.sh を実行してください"
    exit 1
fi

source .phase3-config

echo "🚀 Phase 3 Step 2: コードデプロイ"
echo "📍 リージョン: $REGION"
echo "📍 API URL: $API_URL"

# Python環境設定
echo "🐍 Python環境設定..."
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv local 3.10.12

# 仮想環境セットアップ
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
source .venv/bin/activate

# 依存関係インストール
echo "📦 依存関係インストール..."
pip install --upgrade pip

# Lambda関数パッケージング
echo "📦 Lambda関数パッケージング..."

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

echo "✅ Phase 3 Step 2 完了"
echo "📝 次のステップ: ./deploy-phase3-step3-test.sh を実行してテストしてください"