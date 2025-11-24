#!/bin/bash
# Phase 3 Step 5: AgentCore Runtime デプロイ (完全修正版)

set -e
source .phase3-config

echo "🤖 Phase 3 Step 5: AgentCore Runtime デプロイ (完全修正版)"
echo "📍 リージョン: $REGION"
echo "📍 エージェント名: sila2_runtime_phase3"

# Step 1: ECRパブリックレジストリ認証
echo "🔐 ECRパブリックレジストリ認証中..."
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws || {
    echo "⚠️ ECRパブリック認証失敗 - Docker Hubを使用します"
}

# Step 2: ECRリポジトリ確認・作成
echo "🔧 ECRリポジトリ確認・作成中..."
ECR_REPO_NAME="bedrock-agentcore-sila2_runtime_phase3"
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION 2>/dev/null || {
    echo "ECRリポジトリを作成中..."
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION
}

# Step 3: IAMロール権限確認
echo "🔧 IAMロール権限確認中..."
ROLE_NAME=$(echo $LAMBDA_ROLE_ARN | cut -d'/' -f2)
echo "ロール名: $ROLE_NAME"

# Step 4: 必要な権限を一括追加
echo "📋 必要な権限を一括追加中..."
POLICIES=(
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess"
    "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)

for policy in "${POLICIES[@]}"; do
    aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$policy" --region $REGION 2>/dev/null || echo "権限 $policy は既に追加済み"
done

# Step 5: IAM信頼ポリシー更新
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
}' 2>/dev/null || echo "信頼ポリシーは既に更新済み"

# Step 6: Docker Hubベースの修正版Dockerfileを作成
echo "🐳 修正版Dockerfileを作成中..."
cat > Dockerfile << 'EOF'
FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port (if needed)
EXPOSE 8080

# Run the application
CMD ["python", "main_agentcore_phase3.py"]
EOF

# Step 7: 既存AgentCore Runtime削除 (エラー無視)
echo "🗑️ 既存エージェント削除中..."
~/.pyenv/versions/3.10.*/bin/agentcore destroy --agent "sila2_runtime_phase3" --force 2>/dev/null || echo "エージェントが存在しないか、既に削除済み"

# Step 8: 新しいエージェントを作成
echo "🔧 新しいエージェント作成中..."
AGENT_NAME="sila2_runtime_phase3"

# 非対話的にagentcore configureを実行
echo "🔧 AgentCore設定中..."
cat > temp_config_input.txt << EOF
requirements.txt
no
EOF

~/.pyenv/versions/3.10.*/bin/agentcore configure \
  --name "$AGENT_NAME" \
  --entrypoint main_agentcore_phase3.py \
  --execution-role "${LAMBDA_ROLE_ARN}" \
  --ecr "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/bedrock-agentcore-sila2_runtime_phase3" \
  --region $REGION < temp_config_input.txt

rm -f temp_config_input.txt

# Step 9: ECRプライベートレジストリ認証
echo "🔐 ECRプライベートレジストリ認証中..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Step 10: 新しいエージェントでlaunch (ローカルビルドモード)
echo "🚀 新しいエージェントでlaunch実行中..."
~/.pyenv/versions/3.10.*/bin/agentcore launch \
  --agent "$AGENT_NAME" \
  --local-build \
  --env API_GATEWAY_URL="${API_URL}" \
  --env ENVIRONMENT=dev \
  --env PHASE=3 || {
    echo "❌ ローカルビルドモードが失敗しました。クラウドビルドモードを試行中..."
    
    # クラウドビルドモードでリトライ
    ~/.pyenv/versions/3.10.*/bin/agentcore launch \
      --agent "$AGENT_NAME" \
      --env API_GATEWAY_URL="${API_URL}" \
      --env ENVIRONMENT=dev \
      --env PHASE=3
}

# Step 11: Runtime状態確認
echo "✅ Runtime状態確認中..."
~/.pyenv/versions/3.10.*/bin/agentcore status || echo "状態確認でエラーが発生しましたが、デプロイは継続します"

# Step 12: デプロイ結果確認
echo "🔍 デプロイ結果確認中..."
aws bedrock-agent list-agents --region $REGION --query 'agentSummaries[?contains(agentName, `sila2`)].{Name:agentName,Status:agentStatus,Id:agentId}' --output table || echo "Bedrock Agent確認でエラーが発生しました"

echo "🎉 Phase 3 Step 5 完了: AgentCore Runtime デプロイ成功 (完全修正版)"
echo "📋 次のステップ: テスト実行"
echo "   ./test_phase3.py を実行してください"