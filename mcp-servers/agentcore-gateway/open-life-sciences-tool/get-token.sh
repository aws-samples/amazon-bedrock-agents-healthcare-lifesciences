#!/bin/bash
# Fetches a Cognito M2M access token for the Open Life Sciences MCP Gateway.
# Usage: source get-token.sh [APP_NAME]
#   Sets MCP_TOKEN and GATEWAY_URL in the current shell.
#   Then register with: claude mcp add --transport http open-life-sciences "$GATEWAY_URL" --header "Authorization: Bearer $MCP_TOKEN"

APP_NAME=${1:-open-life-sciences-tool}
REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-west-2")}

echo "🔑 Fetching OAuth2 token for $APP_NAME..."

# Retrieve Cognito and Gateway config from SSM
GATEWAY_URL=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/gateway_url" --query Parameter.Value --output text --region "$REGION" 2>/dev/null)
CLIENT_ID=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/machine_client_id" --query Parameter.Value --output text --region "$REGION" 2>/dev/null)
CLIENT_SECRET=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/cognito_secret" --query Parameter.Value --output text --with-decryption --region "$REGION" 2>/dev/null)
COGNITO_DOMAIN=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/cognito_domain" --query Parameter.Value --output text --region "$REGION" 2>/dev/null)
AUTH_SCOPE=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/cognito_auth_scope" --query Parameter.Value --output text --region "$REGION" 2>/dev/null)

# Validate required parameters
if [ -z "$GATEWAY_URL" ] || [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ] || [ -z "$COGNITO_DOMAIN" ] || [ -z "$AUTH_SCOPE" ]; then
  echo "❌ ERROR: Failed to retrieve required parameters from SSM" >&2
  echo "   Ensure the CloudFormation stacks are deployed and you have SSM read permissions" >&2
  return 1 2>/dev/null || exit 1
fi

# Strip protocol prefix for token endpoint
COGNITO_DOMAIN_CLEAN="${COGNITO_DOMAIN#https://}"

# Request token via client_credentials grant
TOKEN_RESPONSE=$(curl -s -X POST "https://${COGNITO_DOMAIN_CLEAN}/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=${AUTH_SCOPE}")

# Extract access token
MCP_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$MCP_TOKEN" ]; then
  echo "❌ ERROR: Failed to get token. Response: $TOKEN_RESPONSE" >&2
  return 1 2>/dev/null || exit 1
fi

export MCP_TOKEN
export GATEWAY_URL

echo "✅ Token obtained successfully"
echo ""
echo "Gateway URL: $GATEWAY_URL"
echo "Token expires in: 60 minutes"
echo ""
echo "Register with Claude Code:"
echo "  claude mcp add --transport http open-life-sciences \"\$GATEWAY_URL\" --header \"Authorization: Bearer \$MCP_TOKEN\""
echo ""
echo "Or test with curl:"
echo "  curl -X POST \"\$GATEWAY_URL/tools/uniprot_search\" \\"
echo "    -H \"Authorization: Bearer \$MCP_TOKEN\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"query\": \"TP53\", \"max_results\": 5}'"
echo ""
echo "Add to .mcp.json (with environment variable):"
echo "  {\"mcpServers\":{\"open-life-sciences\":{\"type\":\"http\",\"url\":\"$GATEWAY_URL\",\"headers\":{\"Authorization\":\"Bearer \${MCP_TOKEN}\"}}}}"
