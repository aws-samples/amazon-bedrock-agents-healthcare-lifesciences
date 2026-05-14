#!/bin/bash
# Connected Care Platform — Full Deployment Script
# Deploys everything from scratch in a single command.
#
# Usage:
#   ./scripts/deploy.sh                    # Deploy without Memory/KB
#   ./scripts/deploy.sh --with-memory      # Deploy with AgentCore Memory
#   ./scripts/deploy.sh --with-kb          # Deploy with Knowledge Base
#   ./scripts/deploy.sh --full             # Deploy with Memory + KB (recommended)
#   ./scripts/deploy.sh --prefix=my-org    # Custom resource prefix (default: connected-care)
#   ./scripts/deploy.sh --region=us-west-2 # Custom region (default: us-east-1)
#
# Prerequisites:
#   - AWS CLI configured (aws sts get-caller-identity)
#   - Node.js 18+, Python 3.12+, Docker running
#   - CDK bootstrapped: cdk bootstrap aws://ACCOUNT/us-east-1
#   - Bedrock model access enabled for Claude and Titan Embed in us-east-1
#   - Python packages: pip install bedrock-agentcore boto3
#   - For --with-kb: pip install datasets

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
PREFIX="connected-care"

WITH_MEMORY=false
WITH_KB=false

for arg in "$@"; do
  case $arg in
    --with-memory) WITH_MEMORY=true ;;
    --with-kb)     WITH_KB=true ;;
    --full)        WITH_MEMORY=true; WITH_KB=true ;;
    --region=*)    REGION="${arg#*=}" ;;
    --prefix=*)    PREFIX="${arg#*=}" ;;
  esac
done

echo "============================================"
echo " Connected Care Platform — Deployment"
echo "============================================"
echo "Account:  $ACCOUNT_ID"
echo "Region:   $REGION"
echo "Prefix:   $PREFIX"
echo "Memory:   $WITH_MEMORY"
echo "KB:       $WITH_KB"
echo ""

# --------------------------------------------------
# Step 1: Install dependencies
# --------------------------------------------------
echo "--- Step 1: Installing dependencies ---"

if [ ! -d "$PROJECT_DIR/infrastructure/node_modules" ]; then
  echo "Installing CDK dependencies..."
  npm install --prefix "$PROJECT_DIR/infrastructure"
fi

if [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install --prefix "$PROJECT_DIR/frontend"
fi

# --------------------------------------------------
# Step 2: Deploy all CDK stacks (infra + agents)
# --------------------------------------------------
echo ""
echo "--- Step 2: Deploying CDK stacks ---"
cd "$PROJECT_DIR/infrastructure"
npx cdk deploy --all --require-approval never -c resourcePrefix=$PREFIX
cd "$PROJECT_DIR"

# Capture CDK outputs
echo ""
echo "--- Capturing stack outputs ---"
PROXY_URL=$(aws cloudformation describe-stacks \
  --stack-name ConnectedCareAgentCoreStack \
  --query "Stacks[0].Outputs[?OutputKey=='AgentCoreProxyUrl'].OutputValue" \
  --output text --region $REGION)

FRONTEND_URL=$(aws cloudformation describe-stacks \
  --stack-name ConnectedCareAgentCoreStack \
  --query "Stacks[0].Outputs[?OutputKey=='AgentCoreFrontendUrl'].OutputValue" \
  --output text --region $REGION)

USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name ConnectedCareAgentCoreStack \
  --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolId'].OutputValue" \
  --output text --region $REGION)

CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name ConnectedCareAgentCoreStack \
  --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolClientId'].OutputValue" \
  --output text --region $REGION)

IDENTITY_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name ConnectedCareAgentCoreStack \
  --query "Stacks[0].Outputs[?OutputKey=='CognitoIdentityPoolId'].OutputValue" \
  --output text --region $REGION)

NOVA_SONIC_URL=$(aws cloudformation describe-stacks \
  --stack-name ConnectedCareAgentCoreStack \
  --query "Stacks[0].Outputs[?OutputKey=='NovaSonicUrl'].OutputValue" \
  --output text --region $REGION)

echo "  Proxy URL:        $PROXY_URL"
echo "  Frontend URL:     $FRONTEND_URL"
echo "  User Pool ID:     $USER_POOL_ID"
echo "  Client ID:        $CLIENT_ID"
echo "  Identity Pool ID: $IDENTITY_POOL_ID"
echo "  Nova Sonic URL:   $NOVA_SONIC_URL"

# --------------------------------------------------
# Step 3: Seed demo data
# --------------------------------------------------
echo ""
echo "--- Step 3: Seeding demo data ---"
python3 "$PROJECT_DIR/scripts/seed/seed-all.py"

# --------------------------------------------------
# Step 4: Create AgentCore Memory (optional)
# --------------------------------------------------
MEMORY_ID=""
if [ "$WITH_MEMORY" = true ]; then
  echo ""
  echo "--- Step 4: Creating AgentCore Memory ---"
  MEMORY_ID=$(python3 "$PROJECT_DIR/scripts/setup/create-memory.py" 2>&1 | grep "MEMORY_ID:" | awk '{print $2}')
  echo "  Memory ID: $MEMORY_ID"
fi

# --------------------------------------------------
# Step 5: Create Knowledge Base (optional)
# --------------------------------------------------
KB_ID=""
if [ "$WITH_KB" = true ]; then
  echo ""
  echo "--- Step 5: Creating Knowledge Base ---"

  # Download guidelines
  echo "  Downloading clinical guidelines (~520MB)..."
  cd "$PROJECT_DIR"
  python3 scripts/setup/download-guidelines.py

  # Upload to S3
  echo "  Uploading to S3..."
  aws s3 mb "s3://${PREFIX}-guidelines-$ACCOUNT_ID" --region $REGION 2>/dev/null || true
  aws s3 sync guidelines-data/ "s3://${PREFIX}-guidelines-$ACCOUNT_ID/guidelines/" --quiet

  # Create KB
  KB_ID=$(python3 scripts/setup/create-knowledge-base.py 2>&1 | grep "KNOWLEDGE_BASE_ID:" | awk '{print $2}')
  echo "  Knowledge Base ID: $KB_ID"
  echo "  (Ingestion runs in background — 30-60 min for 37K docs)"
fi

# --------------------------------------------------
# Step 6: Redeploy AgentCore stack with Memory/KB
# --------------------------------------------------
if [ -n "$MEMORY_ID" ] || [ -n "$KB_ID" ]; then
  echo ""
  echo "--- Step 6: Redeploying AgentCore with Memory/KB ---"
  cd "$PROJECT_DIR/infrastructure"

  CONTEXT_ARGS=""
  [ -n "$MEMORY_ID" ] && CONTEXT_ARGS="$CONTEXT_ARGS -c memoryId=$MEMORY_ID"
  [ -n "$KB_ID" ] && CONTEXT_ARGS="$CONTEXT_ARGS -c knowledgeBaseId=$KB_ID"

  npx cdk deploy ConnectedCareAgentCoreStack $CONTEXT_ARGS -c resourcePrefix=$PREFIX --require-approval never
  cd "$PROJECT_DIR"
fi

# --------------------------------------------------
# Step 7: Build and deploy frontend
# --------------------------------------------------
echo ""
echo "--- Step 7: Building and deploying frontend ---"

# Write .env from CDK outputs
cat > "$PROJECT_DIR/frontend/.env" << EOF
VITE_AWS_REGION=$REGION
VITE_COGNITO_USER_POOL_ID=$USER_POOL_ID
VITE_COGNITO_USER_POOL_CLIENT_ID=$CLIENT_ID
VITE_COGNITO_IDENTITY_POOL_ID=$IDENTITY_POOL_ID
VITE_FUNCTION_URL=$PROXY_URL
VITE_NOVA_SONIC_URL=$NOVA_SONIC_URL
EOF

echo "  Generated frontend/.env"

cd "$PROJECT_DIR/frontend"
npm run build
echo "  Syncing to S3..."
aws s3 sync dist/ "s3://${PREFIX}-frontend-$ACCOUNT_ID/" --delete

# Invalidate CloudFront
DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?contains(DomainName,'${PREFIX}-frontend')]].Id" \
  --output text 2>/dev/null | head -1)

if [ -n "$DIST_ID" ] && [ "$DIST_ID" != "None" ]; then
  echo "  Invalidating CloudFront cache..."
  aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" > /dev/null
fi
cd "$PROJECT_DIR"

# --------------------------------------------------
# Done
# --------------------------------------------------
echo ""
echo "============================================"
echo " Deployment Complete"
echo "============================================"
echo ""
echo "Frontend URL: $FRONTEND_URL"
echo ""
echo "Open the URL above, create an account, and sign in."
echo ""
if [ "$WITH_KB" = true ]; then
  echo "Note: Knowledge Base ingestion is still running in the background."
  echo "KB search queries will work once ingestion completes (30-60 min)."
fi
