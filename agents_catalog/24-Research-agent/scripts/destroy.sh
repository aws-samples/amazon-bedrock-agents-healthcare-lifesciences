#!/bin/bash

# Deployment script
# Usage: ./scripts/deploy.sh <project-name> <s3-bucket-name> <ar-policy-id>

set -e
unset -v PROJECT_NAME S3_BUCKET_NAME DATA_PREFIX CODE_PREFIX TIMESTAMP AR_POLICY_ID


TIMESTAMP=$(date +%s)

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install it first."
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check parameters
if [ $# -lt 2 ]; then
    echo "Usage: $0 <project-name> <s3-bucket-name>"
    echo "Example: $0 my-project my-documents-bucket"
    exit 1
fi

# Sync Python environment
uv sync

PROJECT_NAME=${1:-"docs-ar-demo"}
S3_BUCKET_NAME=$2
AR_POLICY_ID=$3

DATA_PREFIX="data"
CODE_PREFIX="code"
CFN_PREFIX="cfn"

# Set default region if not specified
AWS_REGION=${AWS_REGION:-us-east-1}

# Delete Cloudformation stack
aws cloudformation delete-stack --stack-name "$PROJECT_NAME"

# Delete S3 data
echo "Deleting agent code from Amazon S3"
aws s3 rm "s3://${S3_BUCKET_NAME}/${CODE_PREFIX}/" --recursive

echo "Deleting data from Amazon S3"
aws s3 rm "s3://${S3_BUCKET_NAME}/${DATA_PREFIX}/" --recursive

echo "Deleting cfn from Amazon S3"
aws s3 rm "s3://${S3_BUCKET_NAME}/${CFN_PREFIX}/" --recursive

echo "Stack deleted successfully"

export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AR_POLICY_ARN="arn:aws:bedrock:${AWS_REGION}:${ACCOUNT_ID}:automated-reasoning-policy/${AR_POLICY_ID}"

echo "To delete the automated reasoning policy, run the following AWS CLI command:"
echo "aws bedrock delete-automated-reasoning-policy --policy-arn ${AR_POLICY_ARN}"