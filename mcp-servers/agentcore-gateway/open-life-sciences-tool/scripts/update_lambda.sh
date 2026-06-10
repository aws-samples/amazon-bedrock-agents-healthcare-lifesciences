#!/bin/bash
set -e
set -o pipefail

# Update Lambda code without full redeployment
#
# This script packages Lambda code, uploads to S3, and updates the CloudFormation
# Infrastructure Stack with the new S3 key. This is faster than full redeployment
# as it only updates the Lambda function code without recreating other resources.
#
# Usage:
#   ./update_lambda.sh [OPTIONS] [APP_NAME]
#
# Options:
#   -m, --modules LIST   Comma-separated list of modules to include (default: all)
#   -h, --help          Show this help message
#
# Arguments:
#   APP_NAME            Application name (default: open-life-sciences-tool)
#
# Examples:
#   # Update Lambda with all modules
#   ./update_lambda.sh
#
#   # Update with specific modules only
#   ./update_lambda.sh --modules "life_sciences_genomics,life_sciences_proteomics"
#
#   # Update for specific application
#   ./update_lambda.sh my-custom-app

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CFN_DIR="$PROJECT_ROOT/cfn"
DATABASE_LAMBDA_DIR="$PROJECT_ROOT/database-lambda"

# Default configuration
SELECTED_MODULES=""
APP_NAME=""

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

show_help() {
    cat << EOF
Update Lambda code without full redeployment

Usage: $0 [OPTIONS] [APP_NAME]

Options:
  -m, --modules LIST   Comma-separated list of modules to include (default: all)
  -h, --help          Show this help message

Arguments:
  APP_NAME            Application name (default: open-life-sciences-tool)

Examples:
  # Update Lambda with all modules
  $0

  # Update with specific modules only
  $0 --modules "life_sciences_genomics,life_sciences_proteomics"

  # Update for specific application
  $0 my-custom-app

EOF
}

# ---------------------------------------------------------------------------
# Parse Arguments
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--modules)
            SELECTED_MODULES="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            echo "❌ Error: Unknown option $1"
            show_help
            exit 1
            ;;
        *)
            APP_NAME="$1"
            shift
            ;;
    esac
done

# Set defaults
APP_NAME=${APP_NAME:-open-life-sciences-tool}
INFRA_STACK_NAME="${APP_NAME}-infra"

# Detect AWS configuration
REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "")}
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
echo "Lambda Code Update"
echo "========================================"
echo "Region:        $REGION"
echo "Account:       $ACCOUNT_ID"
echo "App Name:      $APP_NAME"
echo "Bucket:        $FULL_BUCKET_NAME"
echo "Stack:         $INFRA_STACK_NAME"
if [[ -n "$SELECTED_MODULES" ]]; then
    echo "Modules:       $SELECTED_MODULES"
else
    echo "Modules:       ALL (default)"
fi
echo "========================================"

# ---------------------------------------------------------------------------
# 1. Package Lambda Code
# ---------------------------------------------------------------------------

echo ""
echo "📦 Packaging Lambda deployment package..."

# Build package_lambda.sh command
PACKAGE_CMD="$SCRIPT_DIR/package_lambda.sh --output $DATABASE_LAMBDA_DIR"
if [[ -n "$SELECTED_MODULES" ]]; then
    PACKAGE_CMD="$PACKAGE_CMD --modules $SELECTED_MODULES"
fi

# Execute packaging
if ! $PACKAGE_CMD; then
    echo "❌ Error: Lambda packaging failed"
    exit 1
fi

echo "✅ Lambda package created"

# ---------------------------------------------------------------------------
# 2. Upload to S3
# ---------------------------------------------------------------------------

echo ""
echo "☁️  Uploading Lambda package to S3..."

# Find the most recent ZIP file in database-lambda directory
ZIP_FILE=$(ls -t "$DATABASE_LAMBDA_DIR"/database-function*.zip | head -n 1)

if [[ -z "$ZIP_FILE" || ! -f "$ZIP_FILE" ]]; then
    echo "❌ Error: Lambda ZIP file not found in $DATABASE_LAMBDA_DIR"
    exit 1
fi

ZIP_BASENAME=$(basename "$ZIP_FILE")

# Generate hash for cache busting
HASH=$(shasum -a 256 "$ZIP_FILE" | cut -d' ' -f1 | cut -c1-8)
S3_KEY="lambda-code/database-function-${HASH}.zip"

# Upload to S3
if ! aws s3 cp "$ZIP_FILE" "s3://$FULL_BUCKET_NAME/$S3_KEY" --region "$REGION"; then
    echo "❌ Error: Failed to upload Lambda package to S3"
    exit 1
fi

FILE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)

echo "✅ Lambda package uploaded"
echo "   File:     $ZIP_BASENAME"
echo "   Size:     $FILE_SIZE"
echo "   S3 URI:   s3://$FULL_BUCKET_NAME/$S3_KEY"
echo "   Hash:     $HASH"

# ---------------------------------------------------------------------------
# 3. Update CloudFormation Stack
# ---------------------------------------------------------------------------

echo ""
echo "🚀 Updating CloudFormation stack..."

# Retrieve current stack parameters
CURRENT_PARAMS=$(aws cloudformation describe-stacks \
    --stack-name "$INFRA_STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Parameters' \
    --output json 2>/dev/null || echo "[]")

if [[ "$CURRENT_PARAMS" == "[]" ]]; then
    echo "❌ Error: Stack $INFRA_STACK_NAME not found"
    echo "   Please deploy the stack first using deploy.sh"
    exit 1
fi

# Extract current parameter values (we'll update DatabaseLambdaS3Key)
APP_NAME_PARAM=$(echo "$CURRENT_PARAMS" | jq -r '.[] | select(.ParameterKey=="AppName") | .ParameterValue')
LAMBDA_S3_BUCKET=$(echo "$CURRENT_PARAMS" | jq -r '.[] | select(.ParameterKey=="LambdaS3Bucket") | .ParameterValue')
LITERATURE_S3_KEY=$(echo "$CURRENT_PARAMS" | jq -r '.[] | select(.ParameterKey=="LiteratureLambdaS3Key") | .ParameterValue')

echo "   Current parameters:"
echo "     AppName:              $APP_NAME_PARAM"
echo "     LambdaS3Bucket:       $LAMBDA_S3_BUCKET"
echo "     LiteratureLambdaS3Key: $LITERATURE_S3_KEY"
echo ""
echo "   New parameter:"
echo "     DatabaseLambdaS3Key:  $S3_KEY"
echo ""

# Update stack with new Lambda S3 key
if output=$(aws cloudformation deploy \
    --stack-name "$INFRA_STACK_NAME" \
    --template-file "$CFN_DIR/infrastructure.yaml" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --parameter-overrides \
        "AppName=$APP_NAME_PARAM" \
        "LambdaS3Bucket=$LAMBDA_S3_BUCKET" \
        "DatabaseLambdaS3Key=$S3_KEY" \
        "LiteratureLambdaS3Key=$LITERATURE_S3_KEY" 2>&1); then
    echo "✅ Stack updated successfully"
elif echo "$output" | grep -qi "No changes to deploy"; then
    echo "⚠️  No changes detected in stack (Lambda code was updated but CloudFormation sees no resource changes)"
    echo "   This is expected if only the S3 object content changed."
else
    echo "❌ Error updating stack:"
    echo "$output"
    exit 1
fi

# ---------------------------------------------------------------------------
# 4. Display Lambda Status
# ---------------------------------------------------------------------------

echo ""
echo "========================================"
echo "✅ Lambda Update Complete!"
echo "========================================"

# Retrieve Lambda function details
LAMBDA_ARN=$(aws ssm get-parameter \
    --name "/app/${APP_NAME}/agentcore/database_lambda_arn" \
    --query Parameter.Value \
    --output text \
    --region "$REGION" 2>/dev/null || echo "UNKNOWN")

LAMBDA_STATUS=$(aws lambda get-function \
    --function-name "${APP_NAME}-database" \
    --region "$REGION" \
    --query 'Configuration.[State,LastUpdateStatus]' \
    --output text 2>/dev/null || echo "UNKNOWN UNKNOWN")

LAMBDA_STATE=$(echo "$LAMBDA_STATUS" | awk '{print $1}')
LAMBDA_UPDATE_STATUS=$(echo "$LAMBDA_STATUS" | awk '{print $2}')

echo ""
echo "Lambda Function Details:"
echo "  Name:          ${APP_NAME}-database"
echo "  ARN:           $LAMBDA_ARN"
echo "  State:         $LAMBDA_STATE"
echo "  Update Status: $LAMBDA_UPDATE_STATUS"
echo "  Code S3 Key:   $S3_KEY"
echo "  Code Size:     $FILE_SIZE"
echo "  Code Hash:     $HASH"
echo ""

if [[ "$LAMBDA_STATE" == "Active" && "$LAMBDA_UPDATE_STATUS" == "Successful" ]]; then
    echo "✅ Lambda function is active and ready to use"
elif [[ "$LAMBDA_STATE" == "Pending" ]]; then
    echo "⏳ Lambda function update is in progress..."
    echo "   Wait a few moments and check status with:"
    echo "   aws lambda get-function --function-name ${APP_NAME}-database --region $REGION"
else
    echo "⚠️  Lambda function status: $LAMBDA_STATE / $LAMBDA_UPDATE_STATUS"
    echo "   Check CloudWatch logs for details if needed"
fi

echo ""
echo "========================================"
echo ""
echo "💡 Next steps:"
echo ""
echo "  # Test the updated Lambda function"
echo "  aws lambda invoke --function-name ${APP_NAME}-database \\"
echo "    --region $REGION \\"
echo "    --payload '{\"toolName\": \"uniprot_search\", \"arguments\": {\"query\": \"TP53\", \"max_results\": 1}}' \\"
echo "    response.json"
echo ""
echo "  # Or test via the Gateway endpoint"
echo "  source get-token.sh $APP_NAME"
echo "  GATEWAY_URL=\$(aws ssm get-parameter --name /app/${APP_NAME}/agentcore/gateway_url --query Parameter.Value --output text --region $REGION)"
echo "  curl -X POST \"\$GATEWAY_URL/tools/uniprot_search\" \\"
echo "    -H \"Authorization: Bearer \$MCP_TOKEN\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"query\": \"BRCA1\", \"max_results\": 5}'"
echo ""

