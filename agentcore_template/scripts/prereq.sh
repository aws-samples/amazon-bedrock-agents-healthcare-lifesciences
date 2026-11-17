#!/bin/bash

set -e
set -o pipefail

# ----- Config -----
BUCKET_NAME=${1:-myapp}
INFRA_STACK_NAME=${2:-MyAppStackInfra}
COGNITO_STACK_NAME=${3:-MyAppStackCognito}
INFRA_TEMPLATE_FILE="prerequisite/infrastructure.yaml"
COGNITO_TEMPLATE_FILE="prerequisite/cognito.yaml"
REGION=$(aws configure get region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FULL_BUCKET_NAME="${BUCKET_NAME}-${ACCOUNT_ID}"
ZIP_FILE="lambda.zip"
LAMBDA_SRC="prerequisite/lambda/python"
S3_KEY="${ZIP_FILE}"

# ----- 1. Ensure S3 bucket exists and is owned by this account -----
# The bucket name is predictable, so another account could create it first.
# Never upload Lambda code to a bucket this account does not own.
echo "🪣 Ensuring S3 bucket: $FULL_BUCKET_NAME"
if head_err=$(aws s3api head-bucket --bucket "$FULL_BUCKET_NAME" \
      --expected-bucket-owner "$ACCOUNT_ID" --region "$REGION" 2>&1 >/dev/null); then
  echo "ℹ Bucket exists and is owned by account $ACCOUNT_ID."
elif echo "$head_err" | grep -q "(404)"; then
  # If another account creates the name first, mb fails and set -e stops the script.
  aws s3 mb "s3://$FULL_BUCKET_NAME" --region "$REGION"
  aws s3api wait bucket-exists --bucket "$FULL_BUCKET_NAME" \
    --expected-bucket-owner "$ACCOUNT_ID" --region "$REGION"
else
  echo "❌ Bucket $FULL_BUCKET_NAME exists but is not owned by account $ACCOUNT_ID," >&2
  echo "   or cannot be checked: $head_err" >&2
  echo "   Refusing to upload Lambda code. Re-run with a different bucket name." >&2
  exit 1
fi

# ----- 2. Zip Lambda code -----
echo "📦 Zipping contents of $LAMBDA_SRC into $ZIP_FILE..."
cd "$LAMBDA_SRC"
zip -r "../../../$ZIP_FILE" . > /dev/null
cd - > /dev/null

# ----- 3. Upload to S3 -----
# s3api put-object checks the bucket owner on the write (aws s3 cp cannot).
echo "☁ Uploading $ZIP_FILE to s3://$FULL_BUCKET_NAME/$S3_KEY..."
aws s3api put-object --bucket "$FULL_BUCKET_NAME" --key "$S3_KEY" --body "$ZIP_FILE" \
  --expected-bucket-owner "$ACCOUNT_ID" --region "$REGION" >/dev/null

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
deploy_stack "$INFRA_STACK_NAME" "$INFRA_TEMPLATE_FILE" --parameter-overrides LambdaS3Bucket="$FULL_BUCKET_NAME" LambdaS3Key="$S3_KEY"
infra_exit_code=$?

echo "🔧 Starting deployment of Cognito stack..."
deploy_stack "$COGNITO_STACK_NAME" "$COGNITO_TEMPLATE_FILE"
cognito_exit_code=$?

echo "🔍 Fetching Knowledge Base and Data Source IDs from SSM..."

# ----- 6. Create Knowledge Base -----

python prerequisite/knowledge_base.py --mode create

echo "✅ Deployment complete."