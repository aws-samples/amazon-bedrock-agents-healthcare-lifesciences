#!/bin/bash

# Post-deployment verification script for Open Life Sciences MCP server
# This script validates CloudFormation stack status, OAuth2 authentication,
# and Gateway tool invocation
#
# Usage: ./verify_deployment.sh [APP_NAME]
#   APP_NAME defaults to "open-life-sciences-tool"
#
# Requirements: 10.6

set -e

APP_NAME="${1:-open-life-sciences-tool}"
REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-west-2")}"

# Color output helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function echo_error() {
  echo -e "${RED}❌ $1${NC}" >&2
}

function echo_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

function echo_info() {
  echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo "🔍 Verifying deployment for $APP_NAME in region $REGION"
echo ""

# Track overall status
VERIFICATION_FAILED=0

# ============================================================================
# 1. Check CloudFormation stacks exist and have CREATE_COMPLETE or UPDATE_COMPLETE status
# ============================================================================
echo "📋 Checking CloudFormation stacks..."
STACKS=("${APP_NAME}-infra" "${APP_NAME}-cognito" "${APP_NAME}-agentcore")

for stack in "${STACKS[@]}"; do
  if ! status=$(aws cloudformation describe-stacks \
    --stack-name "$stack" \
    --query 'Stacks[0].StackStatus' \
    --output text \
    --region "$REGION" 2>&1); then
    echo_error "Stack $stack not found or not accessible"
    echo "         Error: $status"
    VERIFICATION_FAILED=1
  elif [[ "$status" == "CREATE_COMPLETE" || "$status" == "UPDATE_COMPLETE" ]]; then
    echo_success "Stack $stack: $status"
  else
    echo_error "Stack $stack has unexpected status: $status"
    VERIFICATION_FAILED=1
  fi
done
echo ""

# ============================================================================
# 2. Retrieve Gateway URL from SSM and verify it is accessible
# ============================================================================
echo "🌐 Retrieving Gateway URL from SSM..."
if ! GATEWAY_URL=$(aws ssm get-parameter \
  --name "/app/${APP_NAME}/agentcore/gateway_url" \
  --query Parameter.Value \
  --output text \
  --region "$REGION" 2>&1); then
  echo_error "Failed to retrieve Gateway URL from SSM"
  echo "         Error: $GATEWAY_URL"
  VERIFICATION_FAILED=1
  GATEWAY_URL=""
else
  echo_success "Gateway URL: $GATEWAY_URL"
  
  # Verify Gateway URL is accessible (should return 401 without auth)
  if ! response=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL" --max-time 10 2>&1); then
    echo_error "Gateway URL is not accessible"
    VERIFICATION_FAILED=1
  elif [[ "$response" == "401" ]]; then
    echo_success "Gateway endpoint is accessible (401 Unauthorized as expected)"
  else
    echo_info "Gateway returned HTTP $response (expected 401)"
  fi
fi
echo ""

# ============================================================================
# 3. Obtain OAuth2 token and verify successful authentication
# ============================================================================
echo "🔑 Obtaining OAuth2 token..."
if [[ -z "$GATEWAY_URL" ]]; then
  echo_error "Skipping token acquisition (Gateway URL not available)"
  VERIFICATION_FAILED=1
  MCP_TOKEN=""
else
  # Retrieve Cognito configuration from SSM
  if ! CLIENT_ID=$(aws ssm get-parameter \
    --name "/app/${APP_NAME}/agentcore/machine_client_id" \
    --query Parameter.Value \
    --output text \
    --region "$REGION" 2>&1); then
    echo_error "Failed to retrieve CLIENT_ID from SSM"
    VERIFICATION_FAILED=1
    MCP_TOKEN=""
  elif ! CLIENT_SECRET=$(aws ssm get-parameter \
    --name "/app/${APP_NAME}/agentcore/cognito_secret" \
    --query Parameter.Value \
    --output text \
    --with-decryption \
    --region "$REGION" 2>&1); then
    echo_error "Failed to retrieve CLIENT_SECRET from SSM"
    VERIFICATION_FAILED=1
    MCP_TOKEN=""
  elif ! COGNITO_DOMAIN=$(aws ssm get-parameter \
    --name "/app/${APP_NAME}/agentcore/cognito_domain" \
    --query Parameter.Value \
    --output text \
    --region "$REGION" 2>&1); then
    echo_error "Failed to retrieve COGNITO_DOMAIN from SSM"
    VERIFICATION_FAILED=1
    MCP_TOKEN=""
  elif ! AUTH_SCOPE=$(aws ssm get-parameter \
    --name "/app/${APP_NAME}/agentcore/cognito_auth_scope" \
    --query Parameter.Value \
    --output text \
    --region "$REGION" 2>&1); then
    echo_error "Failed to retrieve AUTH_SCOPE from SSM"
    VERIFICATION_FAILED=1
    MCP_TOKEN=""
  else
    # Strip protocol prefix for token endpoint
    COGNITO_DOMAIN_CLEAN="${COGNITO_DOMAIN#https://}"
    
    # Request token via client_credentials grant
    if ! TOKEN_RESPONSE=$(curl -s -X POST "https://${COGNITO_DOMAIN_CLEAN}/oauth2/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=${AUTH_SCOPE}" \
      --max-time 10 2>&1); then
      echo_error "Failed to request OAuth2 token"
      echo "         Error: $TOKEN_RESPONSE"
      VERIFICATION_FAILED=1
      MCP_TOKEN=""
    else
      # Extract access token
      if ! MCP_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>&1); then
        echo_error "Failed to extract access token from response"
        echo "         Response: $TOKEN_RESPONSE"
        VERIFICATION_FAILED=1
        MCP_TOKEN=""
      else
        echo_success "OAuth2 token obtained successfully"
        
        # Verify token expiration is 60 minutes
        if EXPIRES_IN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('expires_in', 0))" 2>/dev/null); then
          if [[ "$EXPIRES_IN" == "3600" ]]; then
            echo_success "Token expiration: 60 minutes (as expected)"
          else
            echo_info "Token expiration: $((EXPIRES_IN / 60)) minutes (expected 60)"
          fi
        fi
      fi
    fi
  fi
fi
echo ""

# ============================================================================
# 4. Execute sample tool invocation (uniprot_search for TP53) and verify response format
# ============================================================================
echo "🧪 Testing tool invocation (uniprot_search for TP53)..."
if [[ -z "$MCP_TOKEN" || -z "$GATEWAY_URL" ]]; then
  echo_error "Skipping tool invocation test (token or Gateway URL not available)"
  VERIFICATION_FAILED=1
else
  # Build MCP JSON-RPC request
  MCP_REQUEST='{"jsonrpc": "2.0", "method": "tools/call", "id": 1, "params": {"name": "DatabaseLambda___uniprot_search", "arguments": {"query": "TP53", "max_results": 1}}}'
  
  # Make request to Gateway
  if ! TOOL_RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
    -H "Authorization: Bearer $MCP_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$MCP_REQUEST" \
    --max-time 30 2>&1); then
    echo_error "Tool invocation request failed"
    echo "         Error: $TOOL_RESPONSE"
    VERIFICATION_FAILED=1
  else
    # Verify response is valid JSON
    if ! echo "$TOOL_RESPONSE" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
      echo_error "Tool response is not valid JSON"
      echo "         Response: $TOOL_RESPONSE"
      VERIFICATION_FAILED=1
    else
      # Check if response has "result" field (success) or "error" field (failure)
      if echo "$TOOL_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'result' in d else 1)" 2>/dev/null; then
        echo_success "Tool invocation successful"
        
        # Verify response format (should have "content" array)
        if echo "$TOOL_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'content' in d.get('result', {}) else 1)" 2>/dev/null; then
          echo_success "Response format valid (contains 'content' field)"
          
          # Extract and display sample result
          SAMPLE_RESULT=$(echo "$TOOL_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
content = data.get('result', {}).get('content', [])
if content and isinstance(content, list) and len(content) > 0:
    text = content[0].get('text', '')
    if text:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and 'results' in parsed:
                results = parsed['results']
                print(f'Found {len(results)} result(s)')
                if results:
                    first = results[0]
                    print(f'  Entry: {first.get(\"entry_name\", \"N/A\")}')
                    print(f'  Accession: {first.get(\"accession\", \"N/A\")}')
                    print(f'  Gene: {first.get(\"gene_name\", \"N/A\")}')
            else:
                print('Results structure: ' + str(parsed)[:100])
        except:
            print('Text content: ' + text[:100])
" 2>&1)
          if [[ -n "$SAMPLE_RESULT" ]]; then
            echo_info "$SAMPLE_RESULT"
          fi
        else
          echo_error "Response format invalid (missing 'content' field)"
          VERIFICATION_FAILED=1
        fi
      else
        # Check for error response
        ERROR_MSG=$(echo "$TOOL_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error', {}).get('message', 'Unknown error'))" 2>/dev/null || echo "Failed to parse error")
        echo_error "Tool invocation returned error: $ERROR_MSG"
        VERIFICATION_FAILED=1
      fi
    fi
  fi
fi
echo ""

# ============================================================================
# 5. Display success or failure message with diagnostic information
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $VERIFICATION_FAILED -eq 0 ]]; then
  echo_success "All verification checks passed! 🎉"
  echo ""
  echo "Deployment Summary:"
  echo "  Application: $APP_NAME"
  echo "  Region: $REGION"
  echo "  Gateway URL: $GATEWAY_URL"
  echo ""
  echo "Next Steps:"
  echo "  1. Register with Claude Code:"
  echo "     source get-token.sh $APP_NAME"
  echo "     claude mcp add --transport http open-life-sciences \"\$GATEWAY_URL\" \\"
  echo "       --header \"Authorization: Bearer \$MCP_TOKEN\""
  echo ""
  echo "  2. Or test additional tools:"
  echo "     python tests/test_gateway.py --list-tools"
  echo "     python tests/test_gateway.py --tool uniprot_search --prompt \"BRCA1\""
  echo ""
  exit 0
else
  echo_error "Verification failed - see errors above"
  echo ""
  echo "Diagnostic Information:"
  echo "  Application: $APP_NAME"
  echo "  Region: $REGION"
  echo "  Gateway URL: ${GATEWAY_URL:-<not retrieved>}"
  echo ""
  echo "Troubleshooting:"
  echo "  1. Verify CloudFormation stacks are deployed:"
  echo "     aws cloudformation describe-stacks --stack-name ${APP_NAME}-infra --region $REGION"
  echo ""
  echo "  2. Check SSM parameters exist:"
  echo "     aws ssm get-parameters-by-path --path \"/app/${APP_NAME}/\" --region $REGION"
  echo ""
  echo "  3. Review stack events for errors:"
  echo "     aws cloudformation describe-stack-events --stack-name ${APP_NAME}-agentcore --region $REGION"
  echo ""
  echo "  4. Check Lambda function logs:"
  echo "     aws logs tail /aws/lambda/${APP_NAME}-database --follow --region $REGION"
  echo ""
  exit 1
fi
