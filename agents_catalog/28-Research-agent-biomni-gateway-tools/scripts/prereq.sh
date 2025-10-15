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
ZIP_FILE="prerequisite/database-gateway-function.zip"
LAMBDA_SRC="prerequisite/lambda/python"
S3_KEY="${ZIP_FILE}"
CANCER_BIO_FUNCTION_ZIP="prerequisite/cancer-biology-lambda-function.zip"
CANCER_BIO_LAYER_ZIP="prerequisite/cancer-biology-lambda-layer.zip"
CANCER_BIO_FUNCTION_S3_KEY="${CANCER_BIO_FUNCTION_ZIP}"
CANCER_BIO_LAYER_S3_KEY="${CANCER_BIO_LAYER_ZIP}"

# ----- 1. Create S3 bucket -----
echo "🪣 Using S3 bucket: $FULL_BUCKET_NAME"
if [ "$REGION" = "us-east-1" ]; then
  aws s3api create-bucket \
    --bucket "$FULL_BUCKET_NAME" \
    2>/dev/null || echo "ℹ️ Bucket may already exist or be owned by you."
else
  aws s3api create-bucket \
    --bucket "$FULL_BUCKET_NAME" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION" \
    2>/dev/null || echo "ℹ️ Bucket may already exist or be owned by you."
fi

# ----- 2. Zip Lambda code -----
python prerequisite/create_lambda_zip.py
#echo "📦 Zipping contents of $LAMBDA_SRC into $ZIP_FILE..."
#cd "$LAMBDA_SRC"
#zip -r "../../../$ZIP_FILE" . > /dev/null
#cd - > /dev/null

# ----- 2b. Package Cancer Biology Lambda -----
echo "📦 Packaging Cancer Biology Lambda function and layer..."
python prerequisite/create_cancer_biology_lambda_zip.py

# ----- 3. Upload to S3 -----
echo "☁️ Uploading $ZIP_FILE to s3://$FULL_BUCKET_NAME/$S3_KEY..."
aws s3 cp "$ZIP_FILE" "s3://$FULL_BUCKET_NAME/$S3_KEY"

echo "☁️ Uploading $CANCER_BIO_FUNCTION_ZIP to s3://$FULL_BUCKET_NAME/$CANCER_BIO_FUNCTION_S3_KEY..."
aws s3 cp "$CANCER_BIO_FUNCTION_ZIP" "s3://$FULL_BUCKET_NAME/$CANCER_BIO_FUNCTION_S3_KEY"

echo "☁️ Uploading $CANCER_BIO_LAYER_ZIP to s3://$FULL_BUCKET_NAME/$CANCER_BIO_LAYER_S3_KEY..."
aws s3 cp "$CANCER_BIO_LAYER_ZIP" "s3://$FULL_BUCKET_NAME/$CANCER_BIO_LAYER_S3_KEY"

# ----- 4. Deploy CloudFormation -----
deploy_stack() {
  set +e

  local stack_name=$1
  local template_file=$2
  shift 2
  local params=("$@")

  echo "🚀 Deploying CloudFormation stack: $stack_name"

  output=$(aws cloudformation deploy \
    --stack-name "$stack_name" \
    --template-file "$template_file" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    "${params[@]}" 2>&1)

  exit_code=$?

  echo "$output"

  if [ $exit_code -ne 0 ]; then
    if echo "$output" | grep -qi "No changes to deploy"; then
      echo "ℹ️ No updates for stack $stack_name, continuing..."
      return 0
    else
      echo "❌ Error deploying stack $stack_name:"
      echo "$output"
      return $exit_code
    fi
  else
    echo "✅ Stack $stack_name deployed successfully."
    return 0
  fi
}

# ----- Run both stacks -----
echo "🔧 Starting deployment of infrastructure stack..."
deploy_stack "$INFRA_STACK_NAME" "$INFRA_TEMPLATE_FILE" --parameter-overrides \
  LambdaS3Bucket="$FULL_BUCKET_NAME" \
  LambdaS3Key="$S3_KEY"
infra_exit_code=$?

echo "🔧 Starting deployment of Cognito stack..."
deploy_stack "$COGNITO_STACK_NAME" "$COGNITO_TEMPLATE_FILE"
cognito_exit_code=$?

echo "🔍 Fetching Knowledge Base and Data Source IDs from SSM..."

# ----- 6. Create Knowledge Base -----

python prerequisite/knowledge_base.py --mode create

# ----- 7. Create AgentCore Gateway -----
echo "🌐 Creating AgentCore Gateway..."
python scripts/agentcore_gateway.py create --name researchapp-gw

# ----- 8. Create Cancer Biology Gateway Target -----
echo "🧬 Creating Cancer Biology Gateway Target..."
python scripts/create_cancer_biology_target.py create

echo "✅ Deployment complete."