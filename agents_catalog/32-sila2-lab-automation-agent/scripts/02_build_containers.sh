#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

source "$SCRIPT_DIR/utils/common.sh"

print_header "Building Bridge and Mock Device Containers"

REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
IMAGE_TAG=${IMAGE_TAG:-latest}

print_info "Region: $REGION"
print_info "Account: $ACCOUNT_ID"

# ECRログイン
print_step "Logging in to ECR"
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Bridge Container
print_step "Building Bridge Container"
BRIDGE_REPO="sila2-bridge"
aws ecr describe-repositories --repository-names $BRIDGE_REPO --region $REGION 2>/dev/null || \
  aws ecr create-repository --repository-name $BRIDGE_REPO --region $REGION \
    --image-scanning-configuration scanOnPush=true

cd "$PROJECT_ROOT/bridge_container"
docker build -t $BRIDGE_REPO:$IMAGE_TAG .
docker tag $BRIDGE_REPO:$IMAGE_TAG $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$BRIDGE_REPO:$IMAGE_TAG
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$BRIDGE_REPO:$IMAGE_TAG

# Mock Device Container
print_step "Building Mock Device Container"
MOCK_REPO="sila2-mock-devices"
aws ecr describe-repositories --repository-names $MOCK_REPO --region $REGION 2>/dev/null || \
  aws ecr create-repository --repository-name $MOCK_REPO --region $REGION \
    --image-scanning-configuration scanOnPush=true

mkdir -p "$PROJECT_ROOT/mock_devices/proto"
cp "$PROJECT_ROOT/bridge_container/proto"/*.py "$PROJECT_ROOT/mock_devices/proto/"

cd "$PROJECT_ROOT/mock_devices"
docker build -t $MOCK_REPO:$IMAGE_TAG .
docker tag $MOCK_REPO:$IMAGE_TAG $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$MOCK_REPO:$IMAGE_TAG
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$MOCK_REPO:$IMAGE_TAG

print_success "Both containers built and pushed successfully"
print_info "Bridge: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$BRIDGE_REPO:$IMAGE_TAG"
print_info "Mock: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$MOCK_REPO:$IMAGE_TAG"
