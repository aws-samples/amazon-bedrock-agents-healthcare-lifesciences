#!/bin/bash

set -e
set -o pipefail

# ----- Config -----
BUCKET_NAME=${1:-researchapp}
INFRA_STACK_NAME=${2:-researchappStackInfra}
COGNITO_STACK_NAME=${3:-researchappStackCognito}
INFRA_TEMPLATE_FILE="prerequisite/infrastructure.yaml"
COGNITO_TEMPLATE_FILE="prerequisite/cognito.yaml"
REGION=$(aws configure get region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FULL_BUCKET_NAME="${BUCKET_NAME}-${ACCOUNT_ID}"
DB_ZIP_FILE="prerequisite/database-gateway-function.zip"
LIT_ZIP_FILE="prerequisite/literature-gateway-function.zip"
LAMBDA_SRC="prerequisite/lambda/python"
DB_S3_KEY="${DB_ZIP_FILE}"
LIT_S3_KEY="${LIT_ZIP_FILE}"

# ----- 1. Create S3 bucket -----
echo "🪣 Using S3 bucket: $FULL_BUCKET_NAME"
aws s3 mb "s3://$FULL_BUCKET_NAME" --region "$REGION" 2>/dev/null || \
  echo "ℹ️ Bucket may already exist or be owned by you."

# ----- 2. Zip Lambda code -----
python prerequisite/create_lambda_zip.py

# ----- 3. Upload to S3 -----
echo "☁️ Uploading $DB_ZIP_FILE to s3://$FULL_BUCKET_NAME/$DB_S3_KEY..."
aws s3 cp "$DB_ZIP_FILE" "s3://$FULL_BUCKET_NAME/$DB_S3_KEY"

echo "☁️ Uploading $LIT_ZIP_FILE to s3://$FULL_BUCKET_NAME/$LIT_S3_KEY..."
aws s3 cp "$LIT_ZIP_FILE" "s3://$FULL_BUCKET_NAME/$LIT_S3_KEY"

# ----- 4. Deploy CloudFormation -----
deploy_stack() {
  local stack_name=$1
  local template_file=$2
  shift 2

  echo "🚀 Deploying CloudFormation stack: $stack_name"

  if output=$(aws cloudformation deploy \
    --stack-name "$stack_name" \
    --template-file "$template_file" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    "$@" 2>&1); then
    echo "✅ Stack $stack_name deployed successfully."
    return 0
  elif echo "$output" | grep -qi "No changes to deploy"; then
    echo "ℹ️ No updates for stack $stack_name, continuing..."
    return 0
  else
    echo "❌ Error deploying stack $stack_name:"
    echo "$output"
    return 1
  fi
}

# ----- Run both stacks -----
echo "🔧 Starting deployment of infrastructure stack..."
deploy_stack "$INFRA_STACK_NAME" "$INFRA_TEMPLATE_FILE" --parameter-overrides LambdaS3Bucket="$FULL_BUCKET_NAME" LambdaS3Key="$DB_S3_KEY" LiteratureLambdaS3Key="$LIT_S3_KEY"
infra_exit_code=$?

echo "🔧 Starting deployment of Cognito stack..."
deploy_stack "$COGNITO_STACK_NAME" "$COGNITO_TEMPLATE_FILE"
cognito_exit_code=$?

echo "🔍 Fetching Knowledge Base and Data Source IDs from SSM..."

# ----- 6. Create Knowledge Base -----

python prerequisite/knowledge_base.py --mode create

echo "✅ Deployment complete."

echo ""
echo "📝 IMPORTANT: Update Literature Lambda Environment Variables"
echo "   Before using the literature research functions, update these SSM parameters:"
echo ""
echo "   # Update Anthropic API key for web search and advanced research"
echo "   aws ssm put-parameter --name '/app/researchapp/anthropic_api_key' --value 'your-actual-api-key' --type 'SecureString' --overwrite"
echo ""
echo "   # Update PubMed email for API requests"
echo "   aws ssm put-parameter --name '/app/researchapp/pubmed_email' --value 'your-email@example.com' --type 'String' --overwrite"
echo ""