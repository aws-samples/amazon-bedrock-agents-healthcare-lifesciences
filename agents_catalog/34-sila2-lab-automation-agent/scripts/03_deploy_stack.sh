#!/bin/bash
set -e

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils/config.sh"
source "${SCRIPT_DIR}/utils/common.sh"

# Parse arguments
VPC_ID=""
SUBNET_IDS=""
ROUTE_TABLE_IDS=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --vpc-id)
      VPC_ID="$2"
      shift 2
      ;;
    --subnet-ids)
      SUBNET_IDS="$2"
      shift 2
      ;;
    --route-table-ids)
      ROUTE_TABLE_IDS="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Auto-detect route table IDs if not provided
if [ -z "${ROUTE_TABLE_IDS}" ] && [ -n "${VPC_ID}" ]; then
  echo "Auto-detecting route table IDs..."
  ROUTE_TABLE_IDS=$(aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=${VPC_ID}" \
    --query 'RouteTables[*].RouteTableId' \
    --output text \
    --region "${DEFAULT_REGION}" | tr '\t' ',')
  echo "Found route tables: ${ROUTE_TABLE_IDS}"
fi

# Validate required parameters
if [ -z "${VPC_ID}" ] || [ -z "${SUBNET_IDS}" ] || [ -z "${ROUTE_TABLE_IDS}" ]; then
  echo "Usage: $0 --vpc-id <vpc-id> --subnet-ids <subnet-id-1,subnet-id-2> [--route-table-ids <rtb-id-1,rtb-id-2>]"
  echo "Note: route-table-ids will be auto-detected if not provided"
  exit 1
fi

echo "=== SiLA2 Agent Deployment ==="
echo "VPC ID: ${VPC_ID}"
echo "Subnet IDs: ${SUBNET_IDS}"
echo "Route Table IDs: ${ROUTE_TABLE_IDS}"
echo "Deployment Bucket: ${DEPLOYMENT_BUCKET}"
echo "Region: ${DEFAULT_REGION}"

# Create deployment bucket
create_deployment_bucket "${DEPLOYMENT_BUCKET}"

# Upload nested templates
echo "Uploading nested templates..."
aws s3 cp "${SCRIPT_DIR}/../infrastructure/nested/" "s3://${DEPLOYMENT_BUCKET}/nested/" \
  --recursive --region "${DEFAULT_REGION}"

# Package CloudFormation template
echo "Packaging CloudFormation template..."
aws cloudformation package \
  --template-file "${SCRIPT_DIR}/../infrastructure/main.yaml" \
  --s3-bucket "${DEPLOYMENT_BUCKET}" \
  --output-template-file "/tmp/packaged-main.yaml" \
  --region "${DEFAULT_REGION}"

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file "/tmp/packaged-main.yaml" \
  --stack-name "${MAIN_STACK_NAME}" \
  --parameter-overrides \
    VpcId="${VPC_ID}" \
    PrivateSubnetIds="${SUBNET_IDS}" \
    RouteTableIds="${ROUTE_TABLE_IDS}" \
    DeploymentBucket="${DEPLOYMENT_BUCKET}" \
    EnvironmentName="${ENVIRONMENT_NAME}" \
  --capabilities CAPABILITY_IAM \
  --region "${DEFAULT_REGION}"

echo "=== Deployment Complete ==="
echo "Stack Name: ${MAIN_STACK_NAME}"
echo ""
echo "Outputs:"
aws cloudformation describe-stacks \
  --stack-name "${MAIN_STACK_NAME}" \
  --query 'Stacks[0].Outputs' \
  --output table \
  --region "${DEFAULT_REGION}"
