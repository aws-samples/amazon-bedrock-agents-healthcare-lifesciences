#!/bin/bash

set -e
set -o pipefail

# ----- Config -----
BUCKET_NAME=${1:-researchapp}
INFRA_STACK_NAME=${2:-researchappStackInfra}
COGNITO_STACK_NAME=${3:-researchappStackCognito}
AGENTCORE_STACK_NAME=${4:-researchappStackAgentCore}
INFRA_TEMPLATE_FILE="prerequisite/infrastructure.yaml"
COGNITO_TEMPLATE_FILE="prerequisite/cognito.yaml"
AGENTCORE_STACK_FILE="prerequisite/agentcore.yaml"
REGION=$(aws configure get region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FULL_BUCKET_NAME="${BUCKET_NAME}-${REGION}-${ACCOUNT_ID}"
DB_ZIP_FILE="prerequisite/database-gateway-function.zip"
LIT_ZIP_FILE="prerequisite/literature-gateway-function.zip"

# ----- 1. Create S3 bucket -----
echo "🪣 Using S3 bucket: $FULL_BUCKET_NAME"
aws s3 mb "s3://$FULL_BUCKET_NAME" --region "$REGION" 2>/dev/null || \
  echo "ℹ️ Bucket may already exist or be owned by you."

# ----- 2. Zip Lambda code -----
uv run prerequisite/create_lambda_zip.py

# Generate hashes of ZIP files to force Lambda updates when code changes
DB_HASH=$(shasum -a 256 "$DB_ZIP_FILE" | cut -d' ' -f1 | cut -c1-8)
LIT_HASH=$(shasum -a 256 "$LIT_ZIP_FILE" | cut -d' ' -f1 | cut -c1-8)

# Update S3 keys with hashes
DB_S3_KEY="lambda-code/database-gateway-function-${DB_HASH}.zip"
LIT_S3_KEY="lambda-code/literature-gateway-function-${LIT_HASH}.zip"

# API spec file paths
DB_API_SPEC_FILE="prerequisite/lambda-database/api_spec.json"
LIT_API_SPEC_FILE="prerequisite/lambda-literature/api_spec.json"
DB_API_S3_KEY="api-specs/database-api-spec.json"
LIT_API_S3_KEY="api-specs/literature-api-spec.json"

# ----- 3. Upload to S3 -----
echo "☁️ Uploading $DB_ZIP_FILE to s3://$FULL_BUCKET_NAME/$DB_S3_KEY..."
aws s3 cp "$DB_ZIP_FILE" "s3://$FULL_BUCKET_NAME/$DB_S3_KEY"

echo "☁️ Uploading $LIT_ZIP_FILE to s3://$FULL_BUCKET_NAME/$LIT_S3_KEY..."
aws s3 cp "$LIT_ZIP_FILE" "s3://$FULL_BUCKET_NAME/$LIT_S3_KEY"

echo "☁️ Uploading $DB_API_SPEC_FILE to s3://$FULL_BUCKET_NAME/$DB_API_S3_KEY..."
aws s3 cp "$DB_API_SPEC_FILE" "s3://$FULL_BUCKET_NAME/$DB_API_S3_KEY"

echo "☁️ Uploading $LIT_API_SPEC_FILE to s3://$FULL_BUCKET_NAME/$LIT_API_S3_KEY..."
aws s3 cp "$LIT_API_SPEC_FILE" "s3://$FULL_BUCKET_NAME/$LIT_API_S3_KEY"

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
deploy_stack "$INFRA_STACK_NAME" "$INFRA_TEMPLATE_FILE" --parameter-overrides LambdaS3Bucket="$FULL_BUCKET_NAME" DatabaseLambdaS3Key="$DB_S3_KEY" LiteratureLambdaS3Key="$LIT_S3_KEY"
infra_exit_code=$?

echo "🔧 Starting deployment of Cognito stack..."
deploy_stack "$COGNITO_STACK_NAME" "$COGNITO_TEMPLATE_FILE"
cognito_exit_code=$?

echo "🔧 Starting deployment of AgentCore Gateway and Memory stack..."
deploy_stack "$AGENTCORE_STACK_NAME" "$AGENTCORE_STACK_FILE" --parameter-overrides S3Bucket="$FULL_BUCKET_NAME"
agentcore_exit_code=$?

echo "✅ CloudFormation Deployment complete."

# ----- 6. Create Knowledge Base -----

# TODO - Implement deployment of Knowledgebases in CloudFormation
# python prerequisite/knowledge_base.py --mode create
# echo "✅ Deployment complete."

# ----- 7. Optional: Deploy Streamlit UI -----
read -p "🌐 Deploy Streamlit web UI? (y/N): " deploy_streamlit
if [[ "$deploy_streamlit" =~ ^[Yy]$ ]]; then
  STREAMLIT_STACK_NAME=${5:-research-agent-streamlit}
  STREAMLIT_TEMPLATE_FILE="streamlit-deployment-v3.yaml"
  
  # Get Cognito details from SSM
  COGNITO_USER_POOL_ID=$(aws ssm get-parameter --name '/app/researchapp/agentcore/userpool_id' --query 'Parameter.Value' --output text 2>/dev/null || echo "")
  COGNITO_DOMAIN=$(aws ssm get-parameter --name '/app/researchapp/agentcore/cognito_domain' --query 'Parameter.Value' --output text 2>/dev/null || echo "")
  
  if [[ -z "$COGNITO_USER_POOL_ID" || -z "$COGNITO_DOMAIN" ]]; then
    echo "❌ Error: Cognito configuration not found in SSM. Skipping Streamlit deployment."
  else
    echo "🔧 Deploying Streamlit UI stack..."
    
    # Optional: Ask for SSL certificate ARN
    read -p "Enter ACM SSL Certificate ARN (leave empty for self-signed dev cert): " SSL_CERT_ARN
    
    # Optional: Ask for CIDR whitelist
    read -p "Enter CIDR whitelist for ALB access (default: 0.0.0.0/0): " CIDR_WHITELIST
    CIDR_WHITELIST=${CIDR_WHITELIST:-0.0.0.0/0}
    
    # Deploy Streamlit stack
    STREAMLIT_PARAMS=(
      "ResourceName=$STREAMLIT_STACK_NAME"
      "ApplicationLoadBalancerCIDRWhitelist=$CIDR_WHITELIST"
    )
    
    if [[ -n "$SSL_CERT_ARN" ]]; then
      STREAMLIT_PARAMS+=("ApplicationLoadBalancerSSLCertificate=$SSL_CERT_ARN")
    fi
    
    deploy_stack "$STREAMLIT_STACK_NAME" "$STREAMLIT_TEMPLATE_FILE" --parameter-overrides "${STREAMLIT_PARAMS[@]}"
    streamlit_exit_code=$?
    
    if [ $streamlit_exit_code -eq 0 ]; then
      echo ""
      echo "✅ Streamlit UI deployed successfully!"
      echo ""
    fi
  fi
else
  echo "ℹ️ Skipping Streamlit UI deployment"
fi

echo ""
echo "🎉 Deployment complete!"