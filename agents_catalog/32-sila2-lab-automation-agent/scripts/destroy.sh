#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils/config.sh"

ERROR_COUNT=0

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

# Delete Gateway Targets
if [ -n "$GATEWAY_ID" ]; then
  echo "Deleting Gateway Targets..."
  TARGETS_DELETED=true
  for TARGET_ID in "$TARGET1_ID" "$TARGET2_ID"; do
    if [ -n "$TARGET_ID" ]; then
      echo "  Deleting target: ${TARGET_ID}"
      if aws bedrock-agentcore-control delete-gateway-target \
        --gateway-id "$GATEWAY_ID" \
        --target-id "$TARGET_ID" \
        --region "$DEFAULT_REGION" 2>&1; then
        echo "    ✓ Target deletion initiated"
      else
        EXIT_CODE=$?
        echo "    ⚠ Target deletion failed (exit code: $EXIT_CODE)"
        TARGETS_DELETED=false
        ((ERROR_COUNT++))
      fi
      sleep 3
    fi
  done
  
  if [ "$TARGETS_DELETED" = true ]; then
    echo "  Waiting for all targets to be deleted..."
    sleep 15
  fi
fi

# Delete Gateway
if [ -n "$GATEWAY_ID" ]; then
  echo "Deleting Gateway: ${GATEWAY_ID}..."
  if aws bedrock-agentcore-control delete-gateway \
    --gateway-id "$GATEWAY_ID" \
    --region "$DEFAULT_REGION" 2>&1; then
    echo "  ✓ Gateway deletion initiated"
    echo "  Waiting for gateway deletion to complete..."
    sleep 10
  else
    EXIT_CODE=$?
    echo "  ⚠ Gateway deletion failed (exit code: $EXIT_CODE)"
    ((ERROR_COUNT++))
  fi
fi

# Delete Memory
if [ -n "$MEMORY_ID" ]; then
  echo "Deleting Memory: ${MEMORY_ID}..."
  if OUTPUT=$(aws bedrock-agentcore-control delete-memory \
    --memory-id "$MEMORY_ID" \
    --region "$DEFAULT_REGION" 2>&1); then
    echo "  ✓ Memory deletion initiated"
    sleep 5
  else
    if echo "$OUTPUT" | grep -q "ResourceNotFoundException"; then
      echo "  ℹ Memory already deleted"
    else
      echo "  ⚠ Memory deletion failed"
      echo "$OUTPUT"
      ((ERROR_COUNT++))
    fi
  fi
fi

# Delete AgentCore Runtime (after Gateway deletion)
if [ -n "$AGENT_ID" ]; then
  echo "Deleting AgentCore Runtime: ${AGENT_ID}..."
  if OUTPUT=$(aws bedrock-agentcore-control delete-agent-runtime \
    --agent-runtime-id "$AGENT_ID" \
    --region "$DEFAULT_REGION" 2>&1); then
    echo "  ✓ Runtime deletion initiated"
  else
    if echo "$OUTPUT" | grep -q "ResourceNotFoundException"; then
      echo "  ℹ Runtime already deleted"
    else
      echo "  ⚠ Runtime deletion failed"
      echo "$OUTPUT"
      ((ERROR_COUNT++))
    fi
  fi
  echo "  Waiting for runtime deletion to complete..."
  sleep 10
fi

# Verify AgentCore resources are deleted
echo "Verifying AgentCore resources deletion..."
if [ -n "$AGENT_ID" ]; then
  MAX_RETRIES=6
  RETRY_COUNT=0
  while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if RUNTIME_STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
      --agent-runtime-id "$AGENT_ID" \
      --region "$DEFAULT_REGION" \
      --query 'status' \
      --output text 2>/dev/null); then
      if [ "$RUNTIME_STATUS" = "DELETING" ]; then
        echo "  ⏳ Agent Runtime still deleting... (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)"
        sleep 10
        ((RETRY_COUNT++))
      else
        echo "  ⚠ Agent Runtime in unexpected state: $RUNTIME_STATUS"
        ((ERROR_COUNT++))
        break
      fi
    else
      echo "  ✓ Agent Runtime confirmed deleted"
      break
    fi
  done
  
  if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "  ⚠ WARNING: Agent Runtime still exists after ${MAX_RETRIES} retries"
    ((ERROR_COUNT++))
  fi
fi

echo ""
if [ $ERROR_COUNT -gt 0 ]; then
  echo "⚠ WARNING: $ERROR_COUNT error(s) occurred during AgentCore deletion"
  echo "Do you want to continue with CloudFormation deletion? (yes/no)"
  read -r RESPONSE
  if [ "$RESPONSE" != "yes" ]; then
    echo "Aborted by user"
    exit 1
  fi
else
  echo "✓ All AgentCore resources deleted successfully"
  echo "Press ENTER to proceed with CloudFormation stack deletion, or Ctrl+C to abort..."
  read -r
fi

# Delete CloudFormation Stacks
echo "Deleting CloudFormation Stack: ${MAIN_STACK_NAME}..."
aws cloudformation delete-stack \
  --stack-name "$MAIN_STACK_NAME" \
  --region "$DEFAULT_REGION" 2>/dev/null || true

echo "Waiting for main stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name "$MAIN_STACK_NAME" \
  --region "$DEFAULT_REGION" 2>/dev/null || true

echo "Deleting ECR images..."
for REPO in "$ECR_BRIDGE" "$ECR_MOCK"; do
  echo "  Emptying repository: ${REPO}"
  aws ecr batch-delete-image \
    --repository-name "$REPO" \
    --image-ids "$(aws ecr list-images --repository-name "$REPO" --region "$DEFAULT_REGION" --query 'imageIds[*]' --output json 2>/dev/null)" \
    --region "$DEFAULT_REGION" 2>/dev/null || true
done

echo "Deleting ECR Stack: sila2-ecr-stack..."
aws cloudformation delete-stack \
  --stack-name "sila2-ecr-stack" \
  --region "$DEFAULT_REGION" 2>/dev/null || true

echo "Waiting for ECR stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name "sila2-ecr-stack" \
  --region "$DEFAULT_REGION" 2>/dev/null || true

# Delete S3 Bucket
echo "Deleting S3 Bucket: ${DEPLOYMENT_BUCKET}..."
aws s3 rb "s3://${DEPLOYMENT_BUCKET}" --force \
  --region "$DEFAULT_REGION" 2>/dev/null || true

# Cleanup config files
rm -f "$CONFIG_FILE" "$AGENTCORE_CONFIG"

echo "=== Cleanup Complete ==="
