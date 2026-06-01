#!/usr/bin/env bash
# Source this file: source get-token.sh
# Sets FDA_ECFR_TOKEN and FDA_ECFR_URL environment variables

set -euo pipefail

APP_NAME="${1:-fda-ecfr}"
REGION="${AWS_REGION:-us-east-1}"

echo "Retrieving credentials for $APP_NAME..."

CLIENT_ID=$(aws ssm get-parameter --name "/app/$APP_NAME/agentcore/machine_client_id" --query "Parameter.Value" --output text --region "$REGION" 2>/dev/null || \
  aws cloudformation describe-stacks --stack-name "${APP_NAME}-cognito" --query "Stacks[0].Outputs[?OutputKey=='ClientId'].OutputValue" --output text --region "$REGION")

CLIENT_SECRET=$(aws ssm get-parameter --name "/app/$APP_NAME/agentcore/cognito_secret" --with-decryption --query "Parameter.Value" --output text --region "$REGION" 2>/dev/null || \
  aws cognito-idp describe-user-pool-client --user-pool-id "$(aws cloudformation describe-stacks --stack-name "${APP_NAME}-cognito" --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text --region "$REGION")" --client-id "$CLIENT_ID" --query "UserPoolClient.ClientSecret" --output text --region "$REGION")

TOKEN_URL=$(aws ssm get-parameter --name "/app/$APP_NAME/agentcore/cognito_token_url" --query "Parameter.Value" --output text --region "$REGION" 2>/dev/null || \
  aws cloudformation describe-stacks --stack-name "${APP_NAME}-cognito" --query "Stacks[0].Outputs[?OutputKey=='TokenUrl'].OutputValue" --output text --region "$REGION")

# Get OAuth2 token
export FDA_ECFR_TOKEN=$(curl -s -X POST "$TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$CLIENT_ID&client_secret=$CLIENT_SECRET&scope=${APP_NAME}-api/invoke" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

export FDA_ECFR_URL=$(aws ssm get-parameter --name "/app/$APP_NAME/agentcore/mcp_url" --query "Parameter.Value" --output text --region "$REGION" 2>/dev/null || echo "NOT_YET_CONFIGURED")

echo "FDA_ECFR_TOKEN set (${#FDA_ECFR_TOKEN} chars)"
echo "FDA_ECFR_URL=$FDA_ECFR_URL"
