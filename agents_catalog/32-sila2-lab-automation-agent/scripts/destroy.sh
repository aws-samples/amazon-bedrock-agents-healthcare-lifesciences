#!/bin/bash

export PATH="$HOME/.pyenv/shims:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils/config.sh"

echo "=== SiLA2 Agent Cleanup ==="

# Load config from .gateway-config
CONFIG_FILE="${SCRIPT_DIR}/../.gateway-config"
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"
  echo "Configuration loaded from ${CONFIG_FILE}"
fi

# Load AgentCore config from .bedrock_agentcore.yaml
AGENTCORE_CONFIG="${SCRIPT_DIR}/../.bedrock_agentcore.yaml"
if [ -f "$AGENTCORE_CONFIG" ]; then
  echo "Loading AgentCore configuration..."
  AGENT_ID=$(grep 'agent_id:' "$AGENTCORE_CONFIG" | awk '{print $2}')
  MEMORY_ID=$(grep 'memory_id:' "$AGENTCORE_CONFIG" | awk '{print $2}')
  AGENTCORE_REGION=$(grep 'region:' "$AGENTCORE_CONFIG" | head -1 | awk '{print $2}')
  DEFAULT_REGION="${AGENTCORE_REGION:-$DEFAULT_REGION}"
fi

# Delete AgentCore Runtime
if [ -n "$AGENT_ID" ]; then
  echo "Deleting AgentCore Runtime: ${AGENT_ID}..."
  /usr/local/bin/aws bedrock-agentcore-control delete-agent-runtime \
    --agent-runtime-id "$AGENT_ID" \
    --region "$DEFAULT_REGION" 2>/dev/null && echo "  Runtime deleted successfully" || echo "  Runtime deletion failed or already deleted"
fi

# Delete Gateway Targets
if [ -n "$GATEWAY_ID" ]; then
  echo "Deleting Gateway Targets..."
  for TARGET_ID in "$TARGET1_ID" "$TARGET2_ID"; do
    if [ -n "$TARGET_ID" ]; then
      echo "  Deleting target: ${TARGET_ID}"
      /usr/local/bin/aws bedrock-agentcore-control delete-gateway-target \
        --gateway-id "$GATEWAY_ID" \
        --target-id "$TARGET_ID" \
        --region "$DEFAULT_REGION" 2>/dev/null && echo "    Target deleted successfully" || echo "    Target deletion failed or already deleted"
      sleep 2
    fi
  done
  
  # Wait for targets to be deleted
  echo "  Waiting for targets to be deleted..."
  sleep 5
fi

# Delete Gateway
if [ -n "$GATEWAY_ID" ]; then
  echo "Deleting Gateway: ${GATEWAY_ID}..."
  /usr/local/bin/aws bedrock-agentcore-control delete-gateway \
    --gateway-id "$GATEWAY_ID" \
    --region "$DEFAULT_REGION" 2>/dev/null && echo "  Gateway deleted successfully" || echo "  Gateway deletion failed or already deleted"
  sleep 2
fi

# Delete Memory
if [ -n "$MEMORY_ID" ]; then
  echo "Deleting Memory: ${MEMORY_ID}..."
  /usr/local/bin/aws bedrock-agentcore-control delete-memory \
    --memory-id "$MEMORY_ID" \
    --region "$DEFAULT_REGION" 2>/dev/null && echo "  Memory deleted successfully" || echo "  Memory deletion failed or already deleted"
  sleep 2
fi

# Delete CloudFormation Stacks
echo "Deleting CloudFormation Stack: ${MAIN_STACK_NAME}..."
/usr/local/bin/aws cloudformation delete-stack \
  --stack-name "$MAIN_STACK_NAME" \
  --region "$DEFAULT_REGION" 2>/dev/null || true

echo "Waiting for main stack deletion..."
/usr/local/bin/aws cloudformation wait stack-delete-complete \
  --stack-name "$MAIN_STACK_NAME" \
  --region "$DEFAULT_REGION" 2>/dev/null || true

echo "Deleting ECR images..."
for REPO in "$ECR_BRIDGE" "$ECR_MOCK"; do
  echo "  Emptying repository: ${REPO}"
  /usr/local/bin/aws ecr batch-delete-image \
    --repository-name "$REPO" \
    --image-ids "$(/usr/local/bin/aws ecr list-images --repository-name "$REPO" --region "$DEFAULT_REGION" --query 'imageIds[*]' --output json 2>/dev/null)" \
    --region "$DEFAULT_REGION" 2>/dev/null || true
done

echo "Deleting ECR Stack: sila2-ecr-stack..."
/usr/local/bin/aws cloudformation delete-stack \
  --stack-name "sila2-ecr-stack" \
  --region "$DEFAULT_REGION" 2>/dev/null || true

echo "Waiting for ECR stack deletion..."
/usr/local/bin/aws cloudformation wait stack-delete-complete \
  --stack-name "sila2-ecr-stack" \
  --region "$DEFAULT_REGION" 2>/dev/null || true

# Delete S3 Bucket
echo "Deleting S3 Bucket: ${DEPLOYMENT_BUCKET}..."
/usr/local/bin/aws s3 rb "s3://${DEPLOYMENT_BUCKET}" --force \
  --region "$DEFAULT_REGION" 2>/dev/null || true

# Cleanup config files
rm -f "$CONFIG_FILE" "$AGENTCORE_CONFIG"

echo "=== Cleanup Complete ==="
