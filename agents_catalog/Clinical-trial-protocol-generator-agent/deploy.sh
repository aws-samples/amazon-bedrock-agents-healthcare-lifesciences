#!/bin/bash

# Check required parameters
: "${BUCKET_NAME:?Need BUCKET_NAME as 1st argument}"
: "${NAME:?Need NAME as 2nd argument}"
: "${REGION:?Need REGION as 3rd argument}"
: "${BEDROCK_AGENT_SERVICE_ROLE_ARN:?Need BEDROCK_AGENT_SERVICE_ROLE_ARN as 4th argument}"

# Package
aws cloudformation package \
  --template-file clinical-trial-protocol-agent.yaml \
  --s3-bucket "$BUCKET_NAME" \
  --output-template-file clinical-trial-protocol-agent-packaged.yaml \
  --region "$REGION" \
  --force-upload

# Deploy
aws cloudformation deploy \
  --template-file clinical-trial-protocol-agent-packaged.yaml \
  --stack-name "$NAME" \
  --region "$REGION" \
  --parameter-overrides \
    AgentIAMRoleArn="$BEDROCK_AGENT_SERVICE_ROLE_ARN" \
    LayersBucketName="$BUCKET_NAME" \
  --capabilities CAPABILITY_IAM
