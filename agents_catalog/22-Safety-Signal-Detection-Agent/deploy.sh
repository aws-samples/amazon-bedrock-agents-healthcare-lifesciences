#!/bin/bash

# Check required parameters
: "${BUCKET_NAME:?Need BUCKET_NAME}"
: "${REGION:?Need REGION}"
: "${BEDROCK_AGENT_SERVICE_ROLE_ARN:?Need BEDROCK_AGENT_SERVICE_ROLE_ARN}"

# Package
aws cloudformation package \
  --template-file safety-signal-detection-agent-cfn.yaml \
  --s3-bucket "$BUCKET_NAME" \
  --output-template-file safety-signal-detection-agent-packaged.yaml \
  --region "$REGION" \
  --force-upload

# Deploy
aws cloudformation deploy \
  --template-file safety-signal-detection-agent-packaged.yaml \
  --stack-name "safety-signal-detection-agent" \
  --region "$REGION" \
  --parameter-overrides \
    AgentIAMRoleArn="$BEDROCK_AGENT_SERVICE_ROLE_ARN" \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
