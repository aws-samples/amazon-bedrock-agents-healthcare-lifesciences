#!/bin/bash
# Fetches a Cognito M2M access token for the OLS MCP Runtime server.
# Usage: source get-token.sh [APP_NAME]
#   Sets OLS_MCP_TOKEN and OLS_MCP_URL in the current shell.
#
# NOTE: Do NOT use `set -e` — this script is intended to be sourced.

APP_NAME=${1:-ontology-lookup-service}
REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-west-2")}

# Retrieve Cognito and Runtime config from SSM
OLS_MCP_URL=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/mcp_url" --query Parameter.Value --output text --region "$REGION")
CLIENT_ID=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/machine_client_id" --query Parameter.Value --output text --region "$REGION")
CLIENT_SECRET=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/cognito_secret" --query Parameter.Value --output text --region "$REGION")
COGNITO_DOMAIN=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/cognito_domain" --query Parameter.Value --output text --region "$REGION")
AUTH_SCOPE=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/cognito_auth_scope" --query Parameter.Value --output text --region "$REGION")

# Strip protocol prefix for token endpoint
COGNITO_DOMAIN_CLEAN="${COGNITO_DOMAIN#https://}"

# Request token via client_credentials grant
TOKEN_RESPONSE=$(curl -s -X POST "https://${COGNITO_DOMAIN_CLEAN}/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=${AUTH_SCOPE}")

# Extract access token
OLS_MCP_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$OLS_MCP_TOKEN" ]; then
  echo "ERROR: Failed to get token. Response: $TOKEN_RESPONSE" >&2
  return 1 2>/dev/null || exit 1
fi

export OLS_MCP_TOKEN
export OLS_MCP_URL

echo "MCP URL:          $OLS_MCP_URL"
echo "Token expires in: 60 minutes"
echo ""
echo "Register with Claude Code:"
echo "  claude mcp add --transport http --header \"Authorization: Bearer \$OLS_MCP_TOKEN\" ontology-lookup \"\$OLS_MCP_URL\""
echo ""
echo "Or add to .mcp.json:"
echo "  {\"mcpServers\":{\"ontology-lookup\":{\"type\":\"http\",\"url\":\"$OLS_MCP_URL\",\"headers\":{\"Authorization\":\"Bearer \${OLS_MCP_TOKEN}\"}}}}"
