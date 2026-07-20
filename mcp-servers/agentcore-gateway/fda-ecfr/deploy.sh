#!/usr/bin/env bash
set -euo pipefail

# FDA eCFR MCP Server — Deployment Script
# Deploys Lambda + Cognito + AgentCore Gateway target

APP_NAME="${1:-fda-ecfr}"
REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Deploying FDA eCFR MCP Server ==="
echo "App Name: $APP_NAME"
echo "Region:   $REGION"
echo ""

# Step 1: Deploy Cognito stack
echo "[1/4] Deploying Cognito authentication stack..."
aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/cfn/cognito.yaml" \
  --stack-name "${APP_NAME}-cognito" \
  --parameter-overrides AppName="$APP_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION"

# Step 2: Deploy Lambda stack
echo "[2/4] Deploying Lambda function stack..."
aws cloudformation deploy \
  --template-file "$SCRIPT_DIR/cfn/lambda.yaml" \
  --stack-name "${APP_NAME}-lambda" \
  --parameter-overrides AppName="$APP_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION"

# Update Lambda code with actual handler
echo "[3/4] Updating Lambda function code..."
TMPDIR=$(mktemp -d)
cp "$SCRIPT_DIR/index.py" "$TMPDIR/index.py"
(cd "$TMPDIR" && zip -q function.zip index.py)
aws lambda update-function-code \
  --function-name "${APP_NAME}-handler" \
  --zip-file "fileb://$TMPDIR/function.zip" \
  --region "$REGION" > /dev/null
rm -rf "$TMPDIR"

# Step 4: Register with AgentCore Gateway
echo "[4/4] Registering tools with AgentCore Gateway..."
FUNCTION_ARN=$(aws cloudformation describe-stacks \
  --stack-name "${APP_NAME}-lambda" \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionArn'].OutputValue" \
  --output text --region "$REGION")

echo ""
echo "=== Deployment Complete ==="
echo "Lambda ARN: $FUNCTION_ARN"
echo ""
echo "Next steps:"
echo "  1. Register the Lambda as an AgentCore Gateway target:"
echo "     agentcore gateway add-target --name $APP_NAME --lambda-arn $FUNCTION_ARN --tools-file tool_schema.json"
echo "  2. Run: source get-token.sh"
echo "  3. Connect your AI assistant using the MCP URL"
