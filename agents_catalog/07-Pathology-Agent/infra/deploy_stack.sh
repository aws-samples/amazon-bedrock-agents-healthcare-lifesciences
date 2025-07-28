#!/bin/bash

# Configuration variables
ARTIFACTS_BUCKET=XXX
DEFAULT_SUBNETS=subnet-XXX,subnet-XXX,subnet-XXX
DEFAULT_SECURITY_GROUP_ID=sg-01b26d78f9ac60e43
AWS_PROFILE=XXX
STACK_NAME=Agent
TEMPLATE_FILE=infra.yml
REGION=us-east-1

# Set the AWS profile
export AWS_PROFILE=$AWS_PROFILE

echo "Deploying/updating CloudFormation stack: $STACK_NAME"
echo "Using AWS Profile: $AWS_PROFILE"
echo "Template: $TEMPLATE_FILE"
echo "Region: $REGION"

# Package the CloudFormation template
echo "Packaging CloudFormation template..."
aws cloudformation package \
    --template-file $TEMPLATE_FILE \
    --s3-bucket $ARTIFACTS_BUCKET \
    --output-template-file packaged-template.yml \
    --region $REGION \
    --profile $AWS_PROFILE

# Deploy/update the stack
echo "Deploying/updating stack..."
aws cloudformation deploy \
    --template-file packaged-template.yml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        DefaultSubnets=$DEFAULT_SUBNETS \
        DefaultSecurityGroupID=$DEFAULT_SECURITY_GROUP_ID \
        ArtifactsBucket=$ARTIFACTS_BUCKET \
    --region $REGION \
    --profile $AWS_PROFILE

# Check deployment status
if [ $? -eq 0 ]; then
    echo "Stack $STACK_NAME deployed/updated successfully!"
else
    echo "Stack deployment/update failed!"
    exit 1
fi

# Clean up packaged template
rm -f packaged-template.yml

echo "Deployment complete!" 
# 