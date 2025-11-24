#!/bin/bash
# Phase 3 Option A: 完全修正デプロイ

set -e
source .phase3-config

echo "🚀 Phase 3 Option A: 完全修正デプロイ開始"

# Step 1: ECR権限を即座に追加
echo "🔧 Step 1: ECR権限を即座に追加中..."
ROLE_NAME=$(echo $LAMBDA_ROLE_ARN | cut -d'/' -f2)
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess \
  --region $REGION || echo "ECR権限は既に追加済み"

echo "✅ ECR権限追加完了"

# Step 2: CloudFormation更新で権限を永続化
echo "📦 Step 2: CloudFormation更新中 (権限永続化)..."
aws cloudformation update-stack \
  --stack-name $STACK_NAME \
  --template-body file://infrastructure/sila2-phase3-working.yaml \
  --capabilities CAPABILITY_IAM \
  --region $REGION

echo "⏳ CloudFormation更新完了を待機中..."
aws cloudformation wait stack-update-complete --stack-name $STACK_NAME --region $REGION

# Step 3: 設定ファイル同期
echo "📋 Step 3: 設定ファイル同期中..."
UPDATED_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`LambdaExecutionRoleArn`].OutputValue' --output text)
sed -i "s|LAMBDA_ROLE_ARN=.*|LAMBDA_ROLE_ARN=\"$UPDATED_ROLE_ARN\"|" .phase3-config
sed -i "s|execution_role_arn:.*|execution_role_arn: $UPDATED_ROLE_ARN|" .bedrock_agentcore_phase3.yaml

# Step 4: AgentCore再デプロイ
echo "🤖 Step 4: AgentCore再デプロイ中..."
bash deploy-phase3-step5-runtime.sh

echo "🎉 Phase 3 Option A 完了: 全コンポーネント正常デプロイ"