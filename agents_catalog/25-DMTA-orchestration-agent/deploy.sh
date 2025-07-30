#!/bin/bash

# Check required parameters
: "${DEPLOYMENT_BUCKET:?Need DEPLOYMENT_BUCKET}"
: "${AWS_DEFAULT_REGION:?Need AWS_DEFAULT_REGION}"
: "${BEDROCK_AGENT_SERVICE_ROLE_ARN:?Need BEDROCK_AGENT_SERVICE_ROLE_ARN}"
: "${BEDROCK_MODEL_ID:=anthropic.claude-3-5-sonnet-20241022-v2:0}"

# Create Lambda Layer directory
echo "Creating Lambda Layer..."
mkdir -p lambda_layer/python

# Install requirements
echo "Installing dependencies..."
python -m pip install -r action-groups/opentrons-simulator/requirements.txt -t lambda_layer/python

# Create Lambda Layer zip
echo "Creating Lambda Layer zip..."
cd lambda_layer
zip -r opentrons_layer.zip python/
cd - > /dev/null

# Package
aws cloudformation package \
  --template-file dmta-orchestration-agent-cfn.yaml \
  --s3-bucket "$DEPLOYMENT_BUCKET" \
  --output-template-file dmta-orchestration-agent-packaged.yaml \
  --region "$AWS_DEFAULT_REGION" \
  --force-upload

# Deploy
aws cloudformation deploy \
  --template-file dmta-orchestration-agent-packaged.yaml \
  --stack-name "dmta-orchestration-agent" \
  --region "$AWS_DEFAULT_REGION" \
  --parameter-overrides \
    BedrockAgentServiceRoleArn="$BEDROCK_AGENT_SERVICE_ROLE_ARN" \
    BedrockModelId="$BEDROCK_MODEL_ID" \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND

# Cleanup temporary files
echo "Cleaning up temporary files..."
rm -rf lambda_layer/
rm -f dmta-orchestration-agent-packaged.yaml

echo "Deployment completed successfully"
