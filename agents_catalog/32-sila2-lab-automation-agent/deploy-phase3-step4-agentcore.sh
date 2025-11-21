#!/bin/bash

# SiLA2 Lab Automation Agent - Phase 3 Step 4: AgentCore Setup (FIXED)
set -e

# 設定ファイル読み込み
if [ ! -f ".phase3-config" ]; then
    echo "❌ 設定ファイルが見つかりません。先に deploy-phase3-step1-infra.sh を実行してください"
    exit 1
fi

source .phase3-config

AGENT_NAME="sila2_runtime_phase3"
ECR_REPO_NAME="bedrock-agentcore-sila2_runtime_phase3"

echo "🚀 Phase 3 Step 4: AgentCore セットアップ (FIXED)"
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
ROLE_NAME=$(echo $LAMBDA_ROLE_ARN | cut -d'/' -f2)

# ECR権限をIAMロールに追加
echo "📋 IAMロールにECR権限を追加中..."
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess || echo "ECR権限は既に追加済み"

# X-Ray権限をIAMロールに追加
echo "📋 IAMロールにX-Ray権限を追加中..."
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess || echo "X-Ray権限は既に追加済み"

# AgentCore用の信頼ポリシーを作成
cat > agentcore_trust_policy.json << 'EOF'
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

# 信頼ポリシーを更新
aws iam update-assume-role-policy \
    --role-name $ROLE_NAME \
    --policy-document file://agentcore_trust_policy.json

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
rm -f agentcore_trust_policy.json

echo "✅ AgentCore Setup完了 (ECRリポジトリ作成、IAM権限追加、CodeBuild権限設定済み)"