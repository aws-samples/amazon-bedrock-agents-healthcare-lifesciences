#!/bin/bash

# SiLA2 Lab Automation Agent - Phase 3 Step 1: Infrastructure Only
set -e

REGION="us-west-2"
STACK_NAME="sila2-lab-automation-phase3-infra"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Phase 3 Step 1: インフラストラクチャのみデプロイ"
echo "📍 リージョン: $REGION"
echo "📍 アカウント: $ACCOUNT_ID"
echo "📍 スタック名: $STACK_NAME"

# CloudFormation デプロイ
echo "☁️ CloudFormation デプロイ..."
aws cloudformation deploy \
  --template-file infrastructure/sila2-phase3-working.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION \
  --parameter-overrides Environment=dev

# 出力値取得
echo "📋 デプロイ結果取得..."
OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs' \
  --output json)

echo "$OUTPUTS" | jq -r '.[] | "\(.OutputKey): \(.OutputValue)"'

API_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="ApiGatewayUrl") | .OutputValue')
LAMBDA_ROLE_ARN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="LambdaExecutionRoleArn") | .OutputValue')

echo "✅ インフラストラクチャデプロイ完了"
echo "🌐 API URL: $API_URL"
echo "🔑 Lambda Role: $LAMBDA_ROLE_ARN"

# 設定ファイル保存
cat > .phase3-config << EOF
API_URL="$API_URL"
LAMBDA_ROLE_ARN="$LAMBDA_ROLE_ARN"
REGION="$REGION"
ACCOUNT_ID="$ACCOUNT_ID"
STACK_NAME="$STACK_NAME"
EOF

echo "⚙️ 設定ファイル .phase3-config に保存しました"
echo "📝 次のステップ: ./deploy-phase3-step2-code.sh を実行してください"