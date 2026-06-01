#!/usr/bin/env bash
set -euo pipefail

# ICH Guidelines MCP Server — Deployment Script
# Deploys S3 + Knowledge Base + Lambda + Cognito + AgentCore Gateway target

APP_NAME="${1:-ich-guidelines}"
REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Deploying ICH Guidelines MCP Server ==="
echo "App Name: $APP_NAME"
echo "Region:   $REGION"
echo ""

# Step 1: Deploy S3 bucket
echo "[1/6] Deploying S3 bucket for ICH PDFs..."
aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/cfn/knowledge-base.yaml" \
  --stack-name "${APP_NAME}-kb" \
  --parameter-overrides AppName="$APP_NAME" \
  --region "$REGION"

BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${APP_NAME}-kb" \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
  --output text --region "$REGION")

# Step 2: Upload ICH PDFs
echo "[2/6] Uploading ICH guideline PDFs to S3..."
if [ -d "$SCRIPT_DIR/data" ]; then
  aws s3 sync "$SCRIPT_DIR/data/" "s3://$BUCKET_NAME/" \
    --exclude "README.md" --exclude ".DS_Store" --region "$REGION"
else
  echo "  WARNING: No data/ directory found. Upload ICH PDFs manually to s3://$BUCKET_NAME/"
fi

# Step 3: Create Bedrock Knowledge Base (via SDK — not yet in CFN)
echo "[3/6] Creating Bedrock Knowledge Base..."
echo "  NOTE: Knowledge Base creation requires manual setup or SDK script."
echo "  After creating the KB, set the KB_ID in the next step."
echo ""
echo "  Quick setup via console:"
echo "    1. Go to Amazon Bedrock > Knowledge Bases > Create"
echo "    2. Data source: S3, bucket = $BUCKET_NAME"
echo "    3. Embedding model: Titan Embeddings V2"
echo "    4. Vector store: OpenSearch Serverless (auto-create)"
echo "    5. Note the Knowledge Base ID"
echo ""
read -p "  Enter Knowledge Base ID (or press Enter to skip): " KB_ID
KB_ID="${KB_ID:-REPLACE_WITH_KB_ID}"

# Step 4: Deploy Cognito stack
echo "[4/6] Deploying Cognito authentication stack..."
aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/cfn/cognito.yaml" \
  --stack-name "${APP_NAME}-cognito" \
  --parameter-overrides AppName="$APP_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION"

# Step 5: Deploy Lambda stack
echo "[5/6] Deploying Lambda function stack..."
aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/cfn/lambda.yaml" \
  --stack-name "${APP_NAME}-lambda" \
  --parameter-overrides AppName="$APP_NAME" KnowledgeBaseId="$KB_ID" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION"

# Update Lambda code with actual handler
TMPDIR=$(mktemp -d)
cp "$SCRIPT_DIR/index.py" "$TMPDIR/index.py"
(cd "$TMPDIR" && zip -q function.zip index.py)
aws lambda update-function-code \
  --function-name "${APP_NAME}-handler" \
  --zip-file "fileb://$TMPDIR/function.zip" \
  --region "$REGION" > /dev/null
rm -rf "$TMPDIR"

# Step 6: Store parameters
echo "[6/6] Storing SSM parameters..."
FUNCTION_ARN=$(aws cloudformation describe-stacks \
  --stack-name "${APP_NAME}-lambda" \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionArn'].OutputValue" \
  --output text --region "$REGION")

aws ssm put-parameter --name "/app/$APP_NAME/kb_id" --value "$KB_ID" --type String --overwrite --region "$REGION" > /dev/null
aws ssm put-parameter --name "/app/$APP_NAME/bucket_name" --value "$BUCKET_NAME" --type String --overwrite --region "$REGION" > /dev/null

echo ""
echo "=== Deployment Complete ==="
echo "Lambda ARN:  $FUNCTION_ARN"
echo "KB ID:       $KB_ID"
echo "S3 Bucket:   $BUCKET_NAME"
echo ""
echo "Next steps:"
echo "  1. If KB_ID was skipped, create the Knowledge Base and update Lambda env:"
echo "     aws lambda update-function-configuration --function-name ${APP_NAME}-handler --environment Variables={ICH_KB_ID=<your-kb-id>}"
echo "  2. Register the Lambda as an AgentCore Gateway target:"
echo "     agentcore gateway add-target --name $APP_NAME --lambda-arn $FUNCTION_ARN --tools-file tool_schema.json"
echo "  3. Run: source get-token.sh"
echo "  4. Connect your AI assistant using the MCP URL"
