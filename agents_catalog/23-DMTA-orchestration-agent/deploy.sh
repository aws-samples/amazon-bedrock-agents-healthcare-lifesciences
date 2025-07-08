#!/bin/bash

set -e

# Configuration
STACK_NAME="dmta-agent-v2"
REGION=${AWS_DEFAULT_REGION:-us-west-2}
PROJECT_NAME="DMTA-Orchestration"
# Use specified deployment bucket or create unique one
if [ -z "$DEPLOYMENT_BUCKET" ]; then
    BUCKET_NAME="dmta-deployment-$(date +%s)-${RANDOM}"
    CREATE_BUCKET=true
else
    BUCKET_NAME="$DEPLOYMENT_BUCKET"
    CREATE_BUCKET=false
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting DMTA Orchestration Agent deployment...${NC}"

# Check required environment variables
if [ -z "$BEDROCK_AGENT_SERVICE_ROLE_ARN" ]; then
    echo -e "${RED}❌ Error: BEDROCK_AGENT_SERVICE_ROLE_ARN environment variable is required${NC}"
    echo "Please set: export BEDROCK_AGENT_SERVICE_ROLE_ARN=<your-bedrock-agent-role-arn>"
    exit 1
fi

# Create S3 bucket for deployment artifacts if needed
if [ "$CREATE_BUCKET" = true ]; then
    echo -e "${YELLOW}📦 Creating deployment bucket: $BUCKET_NAME${NC}"
    aws s3 mb s3://$BUCKET_NAME --region $REGION
else
    echo -e "${YELLOW}📦 Using specified deployment bucket: $BUCKET_NAME${NC}"
fi

# Package CloudFormation template
echo -e "${YELLOW}📋 Packaging CloudFormation template...${NC}"
aws cloudformation package \
    --template-file dmta-orchestration-agent-cfn.yaml \
    --s3-bucket $BUCKET_NAME \
    --output-template-file packaged-template.yaml \
    --region $REGION

# Deploy CloudFormation stack
echo -e "${YELLOW}🔧 Deploying CloudFormation stack...${NC}"
aws cloudformation deploy \
    --template-file packaged-template.yaml \
    --stack-name $STACK_NAME \
    --region $REGION \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        BedrockAgentServiceRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARN \
        ProjectName=$PROJECT_NAME

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    
    # Get stack outputs
    echo -e "${YELLOW}📋 Stack Outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
        
    echo -e "${GREEN}🎉 DMTA Orchestration Agent is ready for use!${NC}"
    echo -e "${YELLOW}💡 Note: Bedrock Agent creation may take additional time to complete.${NC}"
    
    # Clean up
    echo -e "${YELLOW}🧹 Cleaning up deployment artifacts...${NC}"
    rm -f packaged-template.yaml
    if [ "$CREATE_BUCKET" = true ]; then
        aws s3 rb s3://$BUCKET_NAME --force --region $REGION
    fi
else
    echo -e "${RED}❌ Deployment failed!${NC}"
    # Clean up on failure
    rm -f packaged-template.yaml
    if [ "$CREATE_BUCKET" = true ]; then
        aws s3 rb s3://$BUCKET_NAME --force --region $REGION 2>/dev/null || true
    fi
    exit 1
fi