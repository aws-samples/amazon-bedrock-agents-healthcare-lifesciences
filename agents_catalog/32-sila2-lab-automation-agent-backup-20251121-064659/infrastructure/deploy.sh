#!/bin/bash
set -e

# SiLA2 Lab Automation Agent - AgentCore Deployment Script

# Configuration
BUCKET_NAME=${1:-"your-deployment-bucket"}
REGION=${2:-"us-west-2"}
STACK_NAME_S3="Sila2LabAutomationS3"
STACK_NAME_MAIN="Sila2LabAutomationAgentCore"

echo "Deploying SiLA2 Lab Automation Agent with AgentCore..."
echo "Bucket: $BUCKET_NAME"
echo "Region: $REGION"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Step 1: Deploy S3 bucket if needed
echo "Step 1: Checking/Creating S3 bucket..."
if ! aws s3 ls "s3://$BUCKET_NAME" >/dev/null 2>&1; then
    echo "Creating S3 bucket: $BUCKET_NAME"
    aws cloudformation deploy \
      --template-file "$SCRIPT_DIR/cfn-s3.yaml" \
      --stack-name $STACK_NAME_S3 \
      --parameter-overrides BucketName=$BUCKET_NAME \
      --region $REGION
else
    echo "S3 bucket $BUCKET_NAME already exists"
fi

# Step 2: Package AgentCore application
echo "Step 2: Packaging AgentCore application..."
cd "$PROJECT_ROOT"

# Create deployment package
TEMP_DIR=$(mktemp -d)
cp -r agent/ "$TEMP_DIR/"
cp -r mcp_server/ "$TEMP_DIR/"
cp -r sila2_stub/ "$TEMP_DIR/"
cp main.py "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"
cp config.yaml "$TEMP_DIR/"

# Create zip file
cd "$TEMP_DIR"
zip -r agentcore-package.zip . -x "*.pyc" "__pycache__/*" "*.git*"
cd "$PROJECT_ROOT"

# Step 3: Upload artifacts to S3
echo "Step 3: Uploading artifacts to S3..."
aws s3 cp "$TEMP_DIR/agentcore-package.zip" "s3://$BUCKET_NAME/sila2-lab-automation/agentcore-package.zip"

# Clean up temp directory
rm -rf "$TEMP_DIR"

# Step 4: Deploy AgentCore Runtime stack
echo "Step 4: Deploying AgentCore Runtime stack..."
aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/cfn-sila2-agent.yaml" \
  --stack-name $STACK_NAME_MAIN \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    BucketName=$BUCKET_NAME \
    LambdaKey=sila2-lab-automation/agentcore-package.zip \
  --region $REGION

# Step 5: Get AgentCore Runtime ARN
echo "Step 5: Retrieving AgentCore Runtime information..."
AGENT_RUNTIME_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME_MAIN \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeArn`].OutputValue' \
  --output text \
  --region $REGION)

AGENT_RUNTIME_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME_MAIN \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeId`].OutputValue' \
  --output text \
  --region $REGION)

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "AgentCore Runtime Information:"
echo "  Runtime ARN: $AGENT_RUNTIME_ARN"
echo "  Runtime ID:  $AGENT_RUNTIME_ID"
echo ""
echo "Next steps:"
echo "1. Test AgentCore Runtime:"
echo "   aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id $AGENT_RUNTIME_ID --region $REGION"
echo ""
echo "2. Run Streamlit UI:"
echo "   streamlit run app.py"
echo ""
echo "3. Use Runtime ARN in your application:"
echo "   export AGENT_RUNTIME_ARN=$AGENT_RUNTIME_ARN"
echo ""