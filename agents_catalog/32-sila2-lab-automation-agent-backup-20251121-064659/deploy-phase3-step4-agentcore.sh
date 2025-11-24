#!/bin/bash

# SiLA2 Lab Automation Agent - Phase 3 Step 4: AgentCore Setup (COMPLETE FIX)
set -e

# 設定ファイル読み込み
if [ ! -f ".phase3-config" ]; then
    echo "❌ 設定ファイルが見つかりません。先に deploy-phase3-step1-infra.sh を実行してください"
    exit 1
fi

source .phase3-config

AGENT_NAME="sila2_runtime_phase3_simple"
ECR_REPO_NAME="bedrock-agentcore-sila2_runtime_phase3_simple"

echo "🚀 Phase 3 Step 4: AgentCore セットアップ (COMPLETE FIX)"
echo "📍 リージョン: $REGION"
echo "📍 エージェント名: $AGENT_NAME"

# Step 1: ECRリポジトリ作成
echo "📦 ECRリポジトリ作成中..."
aws ecr create-repository \
  --repository-name $ECR_REPO_NAME \
  --region $REGION 2>/dev/null || echo "ECRリポジトリは既に存在"

# ECRリポジトリURIを取得
ECR_URI=$(aws ecr describe-repositories \
  --repository-names $ECR_REPO_NAME \
  --region $REGION \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "ECR_URI=$ECR_URI" >> .phase3-config
echo "✅ ECRリポジトリ作成完了: $ECR_URI"

# Step 2: IAM信頼ポリシー修正
echo "🔧 Step 2: IAM信頼ポリシー修正..."
ROLE_NAME=$(echo $LAMBDA_ROLE_ARN | awk -F'/' '{print $NF}')
echo "📋 ロール名: $ROLE_NAME"

# ECR権限をIAMロールに追加
echo "📋 IAMロールにECR権限を追加中..."
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess \
  --region $REGION 2>/dev/null || echo "ECR権限は既に追加済み"

# X-Ray権限をIAMロールに追加
echo "📋 IAMロールにX-Ray権限を追加中..."
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess \
  --region $REGION 2>/dev/null || echo "X-Ray権限は既に追加済み"

# 現在の信頼ポリシーを取得して確認
echo "📋 現在の信頼ポリシーを確認中..."
CURRENT_TRUST=$(aws iam get-role --role-name "$ROLE_NAME" --region $REGION --query 'Role.AssumeRolePolicyDocument' --output json 2>/dev/null || echo "{}")

# AgentCore用の信頼ポリシーを作成
cat > agentcore_trust_policy_fixed.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# 信頼ポリシーを強制更新
echo "📋 信頼ポリシーを強制更新中..."
aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document file://agentcore_trust_policy_fixed.json \
    --region $REGION

# 更新確認
sleep 2
echo "📋 信頼ポリシー更新確認中..."
aws iam get-role --role-name "$ROLE_NAME" --region $REGION --query 'Role.AssumeRolePolicyDocument.Statement[?Principal.Service==`bedrock-agentcore.amazonaws.com`]' --output table

echo "✅ IAM信頼ポリシー更新完了"

# Step 3: CodeBuildロール権限設定
echo "🔧 Step 3: CodeBuildロール権限設定..."
CODEBUILD_ROLE_NAME="AmazonBedrockAgentCoreSDKCodeBuild-${REGION}-6648714c89"

# CodeBuildロールにECR権限を追加
echo "📋 CodeBuildロールにECR権限を追加中..."
aws iam attach-role-policy \
  --role-name "$CODEBUILD_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser \
  --region $REGION 2>/dev/null || echo "CodeBuildロールのECR権限は既に追加済み"

# CodeBuildロールにCloudWatchLogs権限を追加
echo "📋 CodeBuildロールにCloudWatchLogs権限を追加中..."
aws iam attach-role-policy \
  --role-name "$CODEBUILD_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess \
  --region $REGION 2>/dev/null || echo "CodeBuildロールのCloudWatchLogs権限は既に追加済み"

# 一時ファイル削除
rm -f agentcore_trust_policy_fixed.json

# Step 4: AgentCore設定を正しいエージェント名で更新
echo "🔧 Step 4: AgentCore設定を正しいエージェント名で更新中..."
~/.pyenv/versions/3.10.*/bin/agentcore configure set-default $AGENT_NAME 2>/dev/null || echo "設定更新をスキップ"

echo "✅ AgentCore Setup完了 (ECRリポジトリ作成、IAM権限追加、信頼ポリシー強制更新、CodeBuild権限設定済み)"
echo "🔄 IAM変更の反映を待機中..."
sleep 5
echo "✅ 準備完了 - 次のステップに進んでください"