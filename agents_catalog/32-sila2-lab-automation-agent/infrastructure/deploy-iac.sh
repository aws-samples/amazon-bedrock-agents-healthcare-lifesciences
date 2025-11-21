#!/bin/bash
set -e

# SiLA2 Lab Automation Agent - Complete IaC Deployment

# Configuration
BUCKET_NAME=${1:-"sila2-lab-automation-$(date +%s)"}
REGION=${2:-"us-west-2"}
STACK_NAME="SiLA2LabAutomationMaster"
CREATE_BUCKET=${3:-"true"}

echo "🚀 Starting complete IaC deployment for SiLA2 Lab Automation Agent"
echo "   Bucket: $BUCKET_NAME"
echo "   Region: $REGION"
echo "   Stack:  $STACK_NAME"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Step 1: Create bootstrap bucket if needed
if [ "$CREATE_BUCKET" = "true" ]; then
    echo "📦 Step 1: Creating bootstrap S3 bucket..."
    aws s3 mb "s3://$BUCKET_NAME" --region $REGION
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket $BUCKET_NAME \
        --versioning-configuration Status=Enabled
fi

# Step 2: Upload CloudFormation templates
echo "📤 Step 2: Uploading CloudFormation templates..."
aws s3 cp "$SCRIPT_DIR/cfn-s3.yaml" "s3://$BUCKET_NAME/templates/cfn-s3.yaml"
aws s3 cp "$SCRIPT_DIR/cfn-sila2-agent.yaml" "s3://$BUCKET_NAME/templates/cfn-sila2-agent.yaml"

# Step 3: Package AgentCore application
echo "📦 Step 3: Packaging AgentCore application..."
cd "$PROJECT_ROOT"

TEMP_DIR=$(mktemp -d)
echo "   Using temp directory: $TEMP_DIR"

# Copy application files
cp -r agent/ "$TEMP_DIR/"
cp -r mcp_server/ "$TEMP_DIR/"
cp -r sila2_stub/ "$TEMP_DIR/"
cp main.py "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"
cp config.yaml "$TEMP_DIR/"

# Create deployment package
cd "$TEMP_DIR"
zip -r agentcore-package.zip . -x "*.pyc" "__pycache__/*" "*.git*" "tests/*"

# Upload package
echo "📤 Step 4: Uploading AgentCore package..."
aws s3 cp agentcore-package.zip "s3://$BUCKET_NAME/sila2-lab-automation/agentcore-package.zip"

# Clean up
cd "$PROJECT_ROOT"
rm -rf "$TEMP_DIR"

# Step 5: Deploy master stack
echo "🏗️  Step 5: Deploying master CloudFormation stack..."
aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/cfn-master.yaml" \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    BucketName=$BUCKET_NAME \
    CreateS3Bucket=false \
  --region $REGION

# Step 6: Get outputs
echo "📋 Step 6: Retrieving deployment information..."
AGENT_RUNTIME_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeArn`].OutputValue' \
  --output text \
  --region $REGION)

AGENT_RUNTIME_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeId`].OutputValue' \
  --output text \
  --region $REGION)

# Step 7: Create environment file
echo "📝 Step 7: Creating environment configuration..."
cat > "$PROJECT_ROOT/.env" << EOF
# SiLA2 Lab Automation Agent - Environment Configuration
AWS_REGION=$REGION
AGENT_RUNTIME_ARN=$AGENT_RUNTIME_ARN
AGENT_RUNTIME_ID=$AGENT_RUNTIME_ID
S3_BUCKET_NAME=$BUCKET_NAME
STACK_NAME=$STACK_NAME
EOF

echo ""
echo "✅ Complete IaC deployment successful!"
echo ""
echo "📊 Deployment Summary:"
echo "   Stack Name:      $STACK_NAME"
echo "   Runtime ARN:     $AGENT_RUNTIME_ARN"
echo "   Runtime ID:      $AGENT_RUNTIME_ID"
echo "   S3 Bucket:       $BUCKET_NAME"
echo "   Region:          $REGION"
echo ""
echo "🔧 Next Steps:"
echo "1. Test AgentCore Runtime:"
echo "   aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id $AGENT_RUNTIME_ID --region $REGION"
echo ""
echo "2. Run Streamlit UI:"
echo "   cd $PROJECT_ROOT && streamlit run app.py"
echo ""
echo "3. Environment variables saved to: $PROJECT_ROOT/.env"
echo ""
echo "🗑️  To clean up:"
echo "   aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
echo "   aws s3 rb s3://$BUCKET_NAME --force"
echo ""