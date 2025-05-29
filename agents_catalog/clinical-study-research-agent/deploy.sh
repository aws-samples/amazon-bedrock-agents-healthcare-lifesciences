#!/bin/bash

# Check required parameters
: "${BUCKET_NAME:?Need BUCKET_NAME as 1st argument}"
: "${NAME:?Need NAME as 2nd argument}"
: "${REGION:?Need REGION as 3rd argument}"
: "${BEDROCK_AGENT_SERVICE_ROLE_ARN:?Need BEDROCK_AGENT_SERVICE_ROLE_ARN as 4th argument}"
: "${IMAGE_BUCKET:?Need IMAGE_BUCKET as 5th argument}"

# Upload layer manually (optional)
aws s3 cp lambdalayers/matplotlib.zip s3://$BUCKET_NAME/lambdalayers/matplotlib.zip

# Package
aws cloudformation package \
  --template-file clinical-study-agent.yaml \
  --s3-bucket "$BUCKET_NAME" \
  --output-template-file clinical-study-agent-packaged.yaml \
  --region "$REGION" \
  --force-upload

# Deploy
aws cloudformation deploy \
  --template-file clinical-study-agent-packaged.yaml \
  --stack-name "$NAME" \
  --region "$REGION" \
  --parameter-overrides \
    AgentIAMRoleArn="$BEDROCK_AGENT_SERVICE_ROLE_ARN" \
    ChartImageBucketName="$IMAGE_BUCKET" LayersBucketName="$BUCKET_NAME"\
  --capabilities CAPABILITY_IAM
