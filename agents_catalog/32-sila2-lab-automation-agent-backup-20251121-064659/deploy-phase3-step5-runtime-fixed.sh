#!/bin/bash
# Phase 3 Step 5: AgentCore Runtime デプロイ (修正版)

set -e
source .phase3-config

echo "🤖 Phase 3 Step 5: AgentCore Runtime デプロイ (修正版)"
echo "📍 リージョン: $REGION"
echo "📍 エージェント名: sila2_runtime_phase3"

# Step 1: ECRリポジトリ確認・作成
echo "🔧 ECRリポジトリ確認・作成中..."
ECR_REPO_NAME="bedrock-agentcore-sila2_runtime_phase3"
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION 2>/dev/null || {
    echo "ECRリポジトリを作成中..."
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION
}

# Step 2: IAMロール権限確認
echo "🔧 IAMロール権限確認中..."
ROLE_NAME=$(echo $LAMBDA_ROLE_ARN | cut -d'/' -f2)
echo "ロール名: $ROLE_NAME"

# Step 3: ECR権限確認・追加
echo "📋 ECR権限確認・追加中..."
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess \
  --region $REGION 2>/dev/null || echo "ECR権限は既に追加済み"

# Step 4: IAM信頼ポリシー更新
echo "📋 IAM信頼ポリシー更新中..."
aws iam update-assume-role-policy --role-name $ROLE_NAME --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "lambda.amazonaws.com",
          "bedrock-agentcore.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}' || echo "信頼ポリシーは既に更新済み"

# Step 5: X-Ray権限追加
echo "📋 X-Ray権限追加中..."
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess \
  --region $REGION 2>/dev/null || echo "X-Ray権限は既に追加済み"

# Step 6: 既存AgentCore Runtime削除・再作成
echo "🚀 既存AgentCore Runtime削除・再作成中..."
AGENT_NAME="sila2_runtime_phase3"

# 既存エージェントを削除
echo "🗑️ 既存エージェント削除中..."
~/.pyenv/versions/3.10.*/bin/agentcore delete --agent "$AGENT_NAME" --force || echo "エージェントが存在しないか、既に削除済み"

# 新しいエージェントを作成 (修正版設定ファイル使用)
echo "🔧 新しいエージェント作成中 (修正版設定ファイル使用)..."
printf "requirements.txt\nno\n" | ~/.pyenv/versions/3.10.*/bin/agentcore configure \
  --name "$AGENT_NAME" \
  --entrypoint main_agentcore_phase3.py \
  --execution-role "${LAMBDA_ROLE_ARN}" \
  --ecr "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/bedrock-agentcore-sila2_runtime_phase3" \
  --region $REGION

# 新しいエージェントでlaunch (ローカルビルドモード)
echo "🚀 新しいエージェントでlaunch実行中 (ローカルビルドモード)..."
~/.pyenv/versions/3.10.*/bin/agentcore launch \
  --agent "$AGENT_NAME" \
  --local-build \
  --env API_GATEWAY_URL="${API_URL}" \
  --env ENVIRONMENT=dev \
  --env PHASE=3

# Step 7: Runtime状態確認
echo "✅ Runtime状態確認中..."
~/.pyenv/versions/3.10.*/bin/agentcore status

echo "🎉 Phase 3 Step 5 完了: AgentCore Runtime デプロイ成功 (修正版)"