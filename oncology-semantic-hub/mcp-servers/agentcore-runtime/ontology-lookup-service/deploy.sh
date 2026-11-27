#!/bin/bash
set -e
set -o pipefail

# Standalone deployment for OLS (Ontology Lookup Service) MCP Server on AgentCore Runtime
# Deploys: Cognito (auth) + OLS MCP server cloned from GitHub + AgentCore Runtime via @aws/agentcore CLI
#
# Usage: ./deploy.sh [APP_NAME]
#   APP_NAME defaults to "ontology-lookup-service"
#   Set AWS_PROFILE and AWS_REGION before running if needed.
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Python 3.12+ with uv installed
#   - npm install -g @aws/agentcore (agentcore CLI)
#   - git (for cloning OLS source)
#   - Docker running (for container build)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFN_DIR="$SCRIPT_DIR/cfn"

# ----- Config -----
APP_NAME=${1:-ontology-lookup-service}
COGNITO_STACK_NAME="${APP_NAME}-cognito"
AGENT_NAME="ols_mcp_server"

REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-west-2")}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "========================================"
echo "OLS MCP Server - AgentCore Runtime Deploy"
echo "========================================"
echo "Region:       $REGION"
echo "Account:      $ACCOUNT_ID"
echo "App Name:     $APP_NAME"
echo "Agent Name:   $AGENT_NAME"
echo "Cognito Stack: $COGNITO_STACK_NAME"
echo "CLI:          @aws/agentcore $(agentcore --version 2>/dev/null || echo 'NOT INSTALLED')"
echo "========================================"

# ----- Preflight checks -----
if ! command -v agentcore &> /dev/null; then
  echo "ERROR: agentcore CLI not found. Install with: npm install -g @aws/agentcore"
  exit 1
fi

if ! docker info &> /dev/null 2>&1; then
  echo "ERROR: Docker is not running. Start Docker Desktop and retry."
  exit 1
fi

# ----- Helper: deploy CloudFormation stack -----
deploy_stack() {
  local stack_name=$1
  local template_file=$2
  shift 2

  echo ""
  echo "Deploying: $stack_name"

  if output=$(aws cloudformation deploy \
    --stack-name "$stack_name" \
    --template-file "$template_file" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    "$@" 2>&1); then
    echo "[OK] $stack_name deployed successfully"
    return 0
  elif echo "$output" | grep -qi "No changes to deploy"; then
    echo "[INFO] No changes for $stack_name"
    return 0
  else
    echo "[ERROR] deploying $stack_name:"
    echo "$output"
    return 1
  fi
}

# ----- 1. Deploy Cognito stack -----
echo ""
echo "--- Step 1: Deploy Cognito authentication ---"
deploy_stack "$COGNITO_STACK_NAME" "$CFN_DIR/cognito.yaml" \
  --parameter-overrides \
    "AppName=$APP_NAME"

# Retrieve Cognito config from SSM
CLIENT_ID=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/machine_client_id" --query Parameter.Value --output text --region "$REGION")
DISCOVERY_URL=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/cognito_discovery_url" --query Parameter.Value --output text --region "$REGION")
AUTH_SCOPE=$(aws ssm get-parameter --name "/app/${APP_NAME}/agentcore/cognito_auth_scope" --query Parameter.Value --output text --region "$REGION")

echo "[OK] Cognito deployed. Client ID: $CLIENT_ID"

# ----- 2. Clone OLS MCP server from GitHub -----
echo ""
echo "--- Step 2: Clone OLS MCP server source ---"
DEPLOY_DIR="$SCRIPT_DIR/.deploy"
OLS_DIR="$DEPLOY_DIR/ols-mcp-server"

mkdir -p "$DEPLOY_DIR"

if [ -d "$OLS_DIR" ]; then
  echo "[INFO] Removing existing OLS clone..."
  rm -rf "$OLS_DIR"
fi

echo "Cloning https://github.com/seandavi/ols-mcp-server.git ..."
git clone --quiet --depth 1 https://github.com/seandavi/ols-mcp-server.git "$OLS_DIR"
echo "[OK] Repository cloned to $OLS_DIR"

# ----- 3. Patch for AgentCore Runtime -----
echo ""
echo "--- Step 3: Patch OLS server for AgentCore Runtime ---"
python3 "$SCRIPT_DIR/patch_ols.py" "$OLS_DIR"

# ----- 4. Generate requirements.txt -----
echo ""
echo "--- Step 4: Generate requirements.txt ---"

cat > "$DEPLOY_DIR/constraints.txt" << 'EOF'
fastmcp>=2.10.5,<3.0.0
EOF

uv pip compile "$OLS_DIR/pyproject.toml" \
  --constraint "$DEPLOY_DIR/constraints.txt" \
  --output-file "$OLS_DIR/requirements.txt"

echo "boto3>=1.35.0" >> "$OLS_DIR/requirements.txt"
echo "[OK] requirements.txt generated"

# ----- 5. Set up agentcore project -----
echo ""
echo "--- Step 5: Configure agentcore project ---"

PROJECT_DIR="$DEPLOY_DIR/agentcore-project"
rm -rf "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create the agentcore project with --no-agent (we'll add one with BYO)
agentcore create \
  --name "OLSMCPServer" \
  --no-agent \
  --defaults

# Add the OLS agent as BYO (bring your own) code with MCP protocol
agentcore add agent \
  --name "$AGENT_NAME" \
  --type byo \
  --build Container \
  --language Python \
  --protocol MCP \
  --code-location "$OLS_DIR" \
  --entrypoint "src/ols_mcp_server/server.py" \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \
  --allowed-clients "$CLIENT_ID" \
  --json

echo "[OK] AgentCore project configured"

# ----- 6. Deploy to AgentCore Runtime -----
echo ""
echo "--- Step 6: Deploy to AgentCore Runtime ---"
echo "  Building container and deploying (this may take several minutes)..."

agentcore deploy --target default --yes --verbose

echo "[OK] Deployment completed"

# ----- 7. Fetch deployed resource info -----
echo ""
echo "--- Step 7: Fetch deployment info ---"

FETCH_OUTPUT=$(agentcore fetch --json 2>/dev/null || agentcore status --json 2>/dev/null || echo "{}")

# Extract MCP URL from the status/fetch output
MCP_URL=$(echo "$FETCH_OUTPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    agents = data.get('agents', data.get('resources', {}).get('agents', []))
    if isinstance(agents, list) and len(agents) > 0:
        agent = agents[0]
        print(agent.get('endpoint', agent.get('url', agent.get('mcp_url', ''))))
    elif isinstance(agents, dict):
        for k, v in agents.items():
            if isinstance(v, dict):
                print(v.get('endpoint', v.get('url', '')))
                break
except Exception:
    pass
" 2>/dev/null)

# If URL not from fetch, try the agentcore status command
if [ -z "$MCP_URL" ]; then
  STATUS_OUTPUT=$(agentcore status --json 2>&1 || true)
  MCP_URL=$(echo "$STATUS_OUTPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for key in ['endpoint', 'url', 'mcp_url']:
        if key in data:
            print(data[key])
            break
    # Try nested
    for section in data.values():
        if isinstance(section, dict):
            for key in ['endpoint', 'url', 'mcp_url']:
                if key in section:
                    print(section[key])
                    break
except Exception:
    pass
" 2>/dev/null)
fi

if [ -z "$MCP_URL" ]; then
  echo "[WARN] Could not auto-detect MCP URL. Run: agentcore status"
  echo "       Then manually store the URL in SSM."
else
  echo "[OK] MCP URL: $MCP_URL"
fi

# ----- 8. Store configuration in SSM -----
echo ""
echo "--- Step 8: Store configuration in SSM ---"

if [ -n "$MCP_URL" ]; then
  aws ssm put-parameter \
    --name "/app/${APP_NAME}/agentcore/mcp_url" \
    --value "$MCP_URL" \
    --type String \
    --overwrite \
    --region "$REGION" \
    --description "OLS MCP Server URL" > /dev/null
  echo "[OK] Stored mcp_url in /app/${APP_NAME}/agentcore/"
fi

# ----- 9. Output results -----
cd "$SCRIPT_DIR"

echo ""
echo "========================================"
echo "[OK] OLS MCP Server Deployment Complete!"
echo "========================================"
echo ""
echo "MCP URL:   ${MCP_URL:-'Run agentcore status to get URL'}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Get token:  source get-token.sh $APP_NAME"
echo "  2. Register:   claude mcp add --transport http --header \"Authorization: Bearer \$OLS_MCP_TOKEN\" ontology-lookup \"\$OLS_MCP_URL\""
echo ""
echo "========================================"
