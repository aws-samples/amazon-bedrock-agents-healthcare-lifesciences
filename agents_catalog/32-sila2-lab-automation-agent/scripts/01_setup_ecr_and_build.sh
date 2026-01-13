#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils/config.sh"
source "${SCRIPT_DIR}/utils/common.sh"

echo "=== Phase 1: ECR Setup & Container Build ==="
echo "Region: ${DEFAULT_REGION}"

# Step 1: ECRリポジトリ作成
echo ""
echo "Step 1/3: Creating ECR repositories..."
aws cloudformation deploy \
  --template-file "${SCRIPT_DIR}/../infrastructure/ecr-only.yaml" \
  --stack-name "sila2-ecr-stack" \
  --region "${DEFAULT_REGION}"

echo "✅ ECR repositories created"

# Step 2: ECRログイン
echo ""
echo "Step 2/3: Logging into ECR..."
ecr_login
echo "✅ ECR login successful"

# Step 3: コンテナビルド&プッシュ
echo ""
echo "Step 3/3: Building and pushing containers..."

echo "Building bridge container..."
build_and_push_image "${SCRIPT_DIR}/../src/bridge" "${ECR_BRIDGE}"
echo "✅ Bridge container pushed"

echo "Building mock devices container..."
build_and_push_image "${SCRIPT_DIR}/../src/devices" "${ECR_MOCK}"
echo "✅ Mock devices container pushed"

# 結果表示
echo ""
echo "=== Setup Complete ==="
aws cloudformation describe-stacks \
  --stack-name "sila2-ecr-stack" \
  --query 'Stacks[0].Outputs' \
  --output table \
  --region "${DEFAULT_REGION}"

echo ""
echo "Container images:"
echo "  Bridge: ${ACCOUNT_ID}.dkr.ecr.${DEFAULT_REGION}.amazonaws.com/${ECR_BRIDGE}:latest"
echo "  Mock:   ${ACCOUNT_ID}.dkr.ecr.${DEFAULT_REGION}.amazonaws.com/${ECR_MOCK}:latest"
