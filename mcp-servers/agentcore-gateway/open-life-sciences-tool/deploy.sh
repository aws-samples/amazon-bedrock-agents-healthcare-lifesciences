#!/bin/bash
set -e
set -o pipefail

# Standalone deployment for Open Life Sciences MCP Server (Gateway only)
# Deploys: Lambda functions + Cognito + AgentCore Gateway
# Does NOT deploy: Agent Runtime, Memory, Streamlit UI
#
# Usage: ./deploy.sh [APP_NAME]
#   APP_NAME defaults to "open-life-sciences-tool"
#   Set AWS_PROFILE and AWS_REGION before running if needed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFN_DIR="$SCRIPT_DIR/cfn"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
DATABASE_LAMBDA_DIR="$SCRIPT_DIR/database-lambda"

# ----- Config -----
APP_NAME=${1:-open-life-sciences-tool}
INFRA_STACK_NAME="${APP_NAME}-infra"
COGNITO_STACK_NAME="${APP_NAME}-cognito"
AGENTCORE_STACK_NAME="${APP_NAME}-agentcore"

REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-west-2")}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
FULL_BUCKET_NAME="${APP_NAME}-${REGION}-${ACCOUNT_ID}"

# Validation
if [[ -z "$ACCOUNT_ID" ]]; then
  echo "❌ Error: Unable to determine AWS account ID. Please configure AWS CLI."
  echo "   Run: aws configure"
  exit 1
fi

if [[ -z "$REGION" ]]; then
  echo "❌ Error: AWS region not configured. Set AWS_REGION or configure AWS CLI."
  echo "   Run: aws configure"
  echo "   Or:  export AWS_REGION=us-west-2"
  exit 1
fi

echo "========================================"
echo "Open Life Sciences MCP Server Deploy"
echo "========================================"
echo "Region:   $REGION"
echo "Account:  $ACCOUNT_ID"
echo "App Name: $APP_NAME"
echo "Bucket:   $FULL_BUCKET_NAME"
echo "Stacks:   $INFRA_STACK_NAME, $COGNITO_STACK_NAME, $AGENTCORE_STACK_NAME"
echo "========================================"

# ----- 1. Create S3 bucket -----
echo ""
echo "🪣 Creating S3 bucket: $FULL_BUCKET_NAME"
if aws s3 mb "s3://$FULL_BUCKET_NAME" --region "$REGION" 2>/dev/null; then
  echo "✅ Bucket created successfully"
else
  echo "ℹ️  Bucket already exists (or creation skipped)"
fi

# ----- 2. Package Lambda code -----
echo ""
echo "📦 Packaging Lambda deployment package..."

cd "$DATABASE_LAMBDA_DIR"

# Create a clean build directory
BUILD_DIR="build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy Lambda function code
cp lambda_function.py "$BUILD_DIR/"

# Install dependencies in the build directory
if [ -f requirements.txt ]; then
  echo "  Installing dependencies..."
  pip install -r requirements.txt -t "$BUILD_DIR" --quiet --upgrade
else
  echo "⚠️  Warning: requirements.txt not found"
fi

# Create ZIP archive
ZIP_FILE="database-function.zip"
cd "$BUILD_DIR"
echo "  Creating ZIP archive..."
zip -r "../$ZIP_FILE" . -q
cd ..

# Clean up build directory
rm -rf "$BUILD_DIR"

echo "✅ Lambda package created: $ZIP_FILE"

# Generate hash for cache busting
DB_HASH=$(shasum -a 256 "$ZIP_FILE" | cut -d' ' -f1 | cut -c1-8)
DB_S3_KEY="lambda-code/database-function-${DB_HASH}.zip"

cd "$SCRIPT_DIR"

# ----- 3. Generate Tool Schemas -----
echo ""
echo "🔧 Generating tool schemas..."

cd "$SCRIPTS_DIR"

if [ -f generate_tool_schema.py ]; then
  python3 generate_tool_schema.py
  echo "✅ Tool schemas generated"
else
  echo "⚠️  Warning: generate_tool_schema.py not found, skipping schema generation"
fi

# Check if schema file exists
DB_API_SPEC_FILE="database-api-spec.json"
if [ ! -f "$DB_API_SPEC_FILE" ]; then
  echo "❌ Error: $DB_API_SPEC_FILE not found after generation"
  exit 1
fi

DB_API_S3_KEY="api-specs/database-api-spec.json"

cd "$SCRIPT_DIR"

# ----- 4. Upload to S3 -----
echo ""
echo "☁️  Uploading artifacts to S3..."

# Upload Lambda ZIP
aws s3 cp "$DATABASE_LAMBDA_DIR/$ZIP_FILE" "s3://$FULL_BUCKET_NAME/$DB_S3_KEY" --region "$REGION"
echo "  ✅ Uploaded Lambda package"

# Upload API spec
aws s3 cp "$SCRIPTS_DIR/$DB_API_SPEC_FILE" "s3://$FULL_BUCKET_NAME/$DB_API_S3_KEY" --region "$REGION"
echo "  ✅ Uploaded API spec"

echo "✅ All artifacts uploaded"

# ----- 5. Deploy CloudFormation stacks -----
deploy_stack() {
  local stack_name=$1
  local template_file=$2
  shift 2

  echo ""
  echo "🚀 Deploying: $stack_name"

  if output=$(aws cloudformation deploy \
    --stack-name "$stack_name" \
    --template-file "$template_file" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    "$@" 2>&1); then
    echo "✅ $stack_name deployed successfully"
    return 0
  elif echo "$output" | grep -qi "No changes to deploy"; then
    echo "ℹ️  No changes for $stack_name"
    return 0
  else
    echo "❌ Error deploying $stack_name:"
    echo "$output"
    return 1
  fi
}

# Stack 1: Infrastructure (Lambdas + IAM roles)
# Note: LiteratureLambdaS3Key uses same package as Database for now (placeholder)
deploy_stack "$INFRA_STACK_NAME" "$CFN_DIR/infrastructure.yaml" \
  --parameter-overrides \
    "AppName=$APP_NAME" \
    "LambdaS3Bucket=$FULL_BUCKET_NAME" \
    "DatabaseLambdaS3Key=$DB_S3_KEY" \
    "LiteratureLambdaS3Key=$DB_S3_KEY"

# Stack 2: Cognito (auth)
deploy_stack "$COGNITO_STACK_NAME" "$CFN_DIR/cognito.yaml" \
  --parameter-overrides \
    "AppName=$APP_NAME"

# Stack 3: AgentCore (Gateway + targets)
deploy_stack "$AGENTCORE_STACK_NAME" "$CFN_DIR/agentcore.yaml" \
  --parameter-overrides \
    "AppName=$APP_NAME" \
    "S3Bucket=$FULL_BUCKET_NAME" \
    "GatewayName=${APP_NAME}-gw"

# ----- 6. Output results -----
echo ""
echo "========================================"
echo "✅ Deployment Complete!"
echo "========================================"

# Retrieve Gateway URL from SSM
GATEWAY_URL=$(aws ssm get-parameter \
  --name "/app/${APP_NAME}/agentcore/gateway_url" \
  --query Parameter.Value \
  --output text \
  --region "$REGION" 2>/dev/null || echo "PENDING")

echo ""
echo "Gateway URL: $GATEWAY_URL"
echo ""
echo "Next steps:"
echo ""
echo "  1. Get OAuth2 token:"
echo "     cd $SCRIPT_DIR"
echo "     source get-token.sh $APP_NAME"
echo ""
echo "  2. Register with MCP client (Claude Code example):"
echo "     claude mcp add --transport http open-life-sciences \\"
echo "       \"\$GATEWAY_URL\" \\"
echo "       --header \"Authorization: Bearer \$MCP_TOKEN\""
echo ""
echo "  3. Or use with Kiro:"
echo "     # Add to your Kiro MCP configuration"
echo ""
echo "  4. Or test with curl:"
echo "     curl -X POST \"\$GATEWAY_URL/tools/uniprot_search\" \\"
echo "       -H \"Authorization: Bearer \$MCP_TOKEN\" \\"
echo "       -H \"Content-Type: application/json\" \\"
echo "       -d '{\"query\": \"BRCA1\", \"max_results\": 5}'"
echo ""
echo "========================================"
echo ""
echo "⚠️  Optional API Keys (for databases requiring authentication):"
echo ""
echo "  # NCBI E-utilities (higher rate limits)"
echo "  aws ssm put-parameter --name '/app/${APP_NAME}/ncbi_api_key' \\"
echo "    --value 'YOUR_KEY' --type 'SecureString' --overwrite --region $REGION"
echo ""
echo "  # NCBI E-utilities (required for some queries)"
echo "  aws ssm put-parameter --name '/app/${APP_NAME}/ncbi_email' \\"
echo "    --value 'your.email@example.com' --type 'String' --overwrite --region $REGION"
echo ""
echo "  # COSMIC (cancer mutation data)"
echo "  aws ssm put-parameter --name '/app/${APP_NAME}/cosmic_api_key' \\"
echo "    --value 'YOUR_KEY' --type 'SecureString' --overwrite --region $REGION"
echo ""
echo "  # ChemSpider (chemical search)"
echo "  aws ssm put-parameter --name '/app/${APP_NAME}/chemspider_api_key' \\"
echo "    --value 'YOUR_KEY' --type 'SecureString' --overwrite --region $REGION"
echo ""
echo "📚 For cleanup instructions, see the README.md file"
echo ""
