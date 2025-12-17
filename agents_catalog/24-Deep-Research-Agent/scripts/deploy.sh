#!/bin/bash

# Deployment script
# Usage: ./scripts/deploy.sh <project-name> <s3-bucket-name>

set -e
unset -v PROJECT_NAME S3_BUCKET_NAME CODE_PREFIX TIMESTAMP


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

PROJECT_NAME=$1
S3_BUCKET_NAME=$2

CODE_PREFIX="code"
CONTAINER_BUILD_CONTEXT="agents"

# Validate the templates first
echo "Validating CloudFormation template..."
aws cloudformation validate-template --template-body file://infrastructure/root.yaml --no-cli-pager
aws cloudformation validate-template --template-body file://infrastructure/container.yaml --no-cli-pager

# Copy agent code to S3
echo "Copying agent definitions to ${S3_BUCKET_NAME}/${CODE_PREFIX}"
zip -r code.zip "${CONTAINER_BUILD_CONTEXT}" -x .\*/\*
aws s3 cp code.zip "s3://${S3_BUCKET_NAME}/${CODE_PREFIX}/"

# Deploy the stack
echo "Deploying CloudFormation stack..."
echo "Stack Name: ${PROJECT_NAME}"
echo "S3 Bucket: ${S3_BUCKET_NAME}"
echo "Code Prefix: ${CODE_PREFIX}"
echo ""

aws cloudformation package --template-file infrastructure/root.yaml --output-template root-packaged.yaml --s3-bucket "${S3_BUCKET_NAME}" --s3-prefix cfn 
aws cloudformation deploy \
    --template-file root-packaged.yaml \
    --stack-name "${PROJECT_NAME}" \
    --parameter-overrides \
        ProjectName="${PROJECT_NAME}" \
        S3CodeBucket="${S3_BUCKET_NAME}" \
        S3CodeKey="${CODE_PREFIX}/code.zip" \
        BuildContextPath="${CONTAINER_BUILD_CONTEXT}" \
        Timestamp="${TIMESTAMP}" \
        WaitForCodeBuild="Y" \
    --capabilities CAPABILITY_IAM \
    --tags Project="${PROJECT_NAME}" Component=Infrastructure

echo "Deployment completed successfully!"
echo "Stack outputs:"
aws cloudformation describe-stacks --stack-name "${PROJECT_NAME}" --query 'Stacks[0].Outputs' --output table

# Clean up
echo "Cleaning up"
rm code.zip
rm root-packaged.yaml