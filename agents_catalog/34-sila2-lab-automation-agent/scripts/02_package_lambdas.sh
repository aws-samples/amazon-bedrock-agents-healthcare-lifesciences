#!/bin/bash
set -e

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils/config.sh"
source "${SCRIPT_DIR}/utils/common.sh"

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it first."
    echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

if ! command -v zip &> /dev/null; then
    echo "Error: zip command is not found. Please install zip utility."
    exit 1
fi

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

# Install bedrock-agentcore and boto3
echo "Installing bedrock-agentcore and boto3..."
python3 -m pip install bedrock-agentcore boto3 botocore -t "${TEMP_DIR}" --upgrade --quiet

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

# Install requests
cd /tmp
python3 -m pip install requests -t "${LAYER_DIR}/python" --upgrade --quiet

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
