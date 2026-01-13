#!/bin/bash
set -e

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils/config.sh"
source "${SCRIPT_DIR}/utils/common.sh"

echo "=== Lambda Function Packaging ==="
echo "Deployment Bucket: ${DEPLOYMENT_BUCKET}"
echo "Region: ${DEFAULT_REGION}"

# Create deployment bucket if not exists
create_deployment_bucket "${DEPLOYMENT_BUCKET}"

# Package analyze_heating_rate Lambda
echo "Packaging analyze_heating_rate Lambda..."
cd "${SCRIPT_DIR}/../src/lambda/tools/analyze_heating_rate"
zip -r /tmp/analyze_heating_rate.zip . -x "*.pyc" "__pycache__/*"
aws s3 cp /tmp/analyze_heating_rate.zip "s3://${DEPLOYMENT_BUCKET}/lambda/" --region "${DEFAULT_REGION}"
echo "✅ analyze_heating_rate packaged"

# Package proxy Lambda (if needed for updates)
echo "Packaging proxy Lambda..."
cd "${SCRIPT_DIR}/../src/lambda/proxy"
zip -r /tmp/proxy.zip . -x "*.pyc" "__pycache__/*"
aws s3 cp /tmp/proxy.zip "s3://${DEPLOYMENT_BUCKET}/lambda/" --region "${DEFAULT_REGION}"
echo "✅ proxy packaged"

# Package invoker Lambda with dependencies
echo "Packaging invoker Lambda..."
cd "${SCRIPT_DIR}/../src/lambda/invoker"

# Create temporary directory for packaging
TEMP_DIR="/tmp/invoker_package"
rm -rf "${TEMP_DIR}"
mkdir -p "${TEMP_DIR}"

# Copy Lambda code
cp lambda_function.py "${TEMP_DIR}/"

# Install bedrock-agentcore and boto3 using Python 3.10
echo "Installing bedrock-agentcore and boto3 for Python 3.10..."
~/.pyenv/versions/3.10.12/bin/pip install bedrock-agentcore boto3 botocore -t "${TEMP_DIR}" --upgrade

# Create zip
cd "${TEMP_DIR}"
zip -r /tmp/invoker.zip . -x "*.pyc" "__pycache__/*"
aws s3 cp /tmp/invoker.zip "s3://${DEPLOYMENT_BUCKET}/lambda/" --region "${DEFAULT_REGION}"

# Cleanup
rm -rf "${TEMP_DIR}"
echo "✅ invoker packaged with bedrock-agentcore"

# Create requests Lambda Layer for Python 3.10
echo "Creating requests Lambda Layer..."
LAYER_DIR="/tmp/requests_layer"
rm -rf "${LAYER_DIR}"
mkdir -p "${LAYER_DIR}/python"

# Install requests from a stable directory
cd /tmp
~/.pyenv/versions/3.10.12/bin/pip install requests -t "${LAYER_DIR}/python" --upgrade

# Create zip from the layer directory
cd "${LAYER_DIR}"
zip -r /tmp/requests_layer.zip python
aws s3 cp /tmp/requests_layer.zip "s3://${DEPLOYMENT_BUCKET}/lambda/" --region "${DEFAULT_REGION}"

# Publish Lambda Layer
LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name sila2-requests-layer \
  --description "Requests library for Python 3.10" \
  --zip-file fileb:///tmp/requests_layer.zip \
  --compatible-runtimes python3.10 \
  --region "${DEFAULT_REGION}" \
  --query 'LayerVersionArn' \
  --output text)

echo "✅ Lambda Layer created: ${LAYER_ARN}"
echo "${LAYER_ARN}" > /tmp/requests_layer_arn.txt

# Cleanup
rm -rf "${LAYER_DIR}"
echo "✅ requests layer packaged"

echo ""
echo "=== Lambda Packaging Complete ==="
echo "All Lambda functions uploaded to s3://${DEPLOYMENT_BUCKET}/lambda/"
