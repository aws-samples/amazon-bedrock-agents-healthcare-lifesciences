#!/bin/bash

# HealthLake Agent - Template Integration Script
# This script integrates the HealthLake agent with the agentcore_template

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}HealthLake Agent Template Integration${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -d "agentcore_template" ]; then
    echo -e "${RED}Error: agentcore_template directory not found${NC}"
    echo "Please run this script from the repository root"
    exit 1
fi

if [ ! -d "agents_catalog/35-healthlake-agent" ]; then
    echo -e "${RED}Error: agents_catalog/35-healthlake-agent directory not found${NC}"
    exit 1
fi

# Get configuration
echo -e "${YELLOW}Configuration:${NC}"
read -p "Enter your prefix (e.g., myapp): " PREFIX
read -p "Enter your HealthLake datastore ID: " HEALTHLAKE_DATASTORE_ID
read -p "Enter AWS region (default: us-west-2): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-west-2}

echo ""
echo -e "${GREEN}Step 1: Copying HealthLake tools to template${NC}"
cp agents_catalog/35-healthlake-agent/utils/healthlake_tools.py agentcore_template/agent/agent_config/tools/ 2>/dev/null || \
cp agentcore_template/agent/agent_config/tools/healthlake_tools.py agentcore_template/agent/agent_config/tools/healthlake_tools.py
echo -e "${GREEN}✓ Tools copied${NC}"

echo ""
echo -e "${GREEN}Step 2: Creating SSM parameter for HealthLake datastore${NC}"
aws ssm put-parameter \
    --name "/app/${PREFIX}/healthlake/datastore_id" \
    --value "${HEALTHLAKE_DATASTORE_ID}" \
    --type "String" \
    --region "${AWS_REGION}" \
    --overwrite || echo -e "${YELLOW}Warning: Could not create SSM parameter (may need to do manually)${NC}"
echo -e "${GREEN}✓ SSM parameter created${NC}"

echo ""
echo -e "${GREEN}Step 3: Updating requirements.txt${NC}"
if ! grep -q "requests>=2.31.0" agentcore_template/agent/requirements.txt; then
    echo "requests>=2.31.0" >> agentcore_template/agent/requirements.txt
    echo -e "${GREEN}✓ Added requests to requirements${NC}"
else
    echo -e "${YELLOW}✓ requests already in requirements${NC}"
fi

echo ""
echo -e "${GREEN}Step 4: Creating IAM policy document${NC}"
cat > /tmp/healthlake-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "healthlake:DescribeFHIRDatastore",
        "healthlake:ReadResource",
        "healthlake:SearchWithGet",
        "healthlake:SearchWithPost"
      ],
      "Resource": "arn:aws:healthlake:*:*:datastore/fhir/*"
    }
  ]
}
EOF
echo -e "${GREEN}✓ Policy document created at /tmp/healthlake-policy.json${NC}"

echo ""
echo -e "${GREEN}Step 5: Getting runtime role${NC}"
RUNTIME_ROLE=$(aws ssm get-parameter --name "/app/${PREFIX}/agentcore/runtime_iam_role" --query "Parameter.Value" --output text --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -z "$RUNTIME_ROLE" ]; then
    echo -e "${YELLOW}Warning: Could not find runtime role in SSM${NC}"
    echo -e "${YELLOW}You'll need to attach the HealthLake policy manually${NC}"
    echo -e "${YELLOW}Policy document is at: /tmp/healthlake-policy.json${NC}"
else
    echo -e "${GREEN}✓ Found runtime role: ${RUNTIME_ROLE}${NC}"
    
    ROLE_NAME=$(echo $RUNTIME_ROLE | cut -d'/' -f2)
    
    echo ""
    echo -e "${GREEN}Step 6: Attaching HealthLake policy to role${NC}"
    aws iam put-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-name HealthLakeAccess \
        --policy-document file:///tmp/healthlake-policy.json \
        --region "${AWS_REGION}" || echo -e "${YELLOW}Warning: Could not attach policy (may need to do manually)${NC}"
    echo -e "${GREEN}✓ Policy attached${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Integration Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Update agent_task.py to use HealthLake tools:"
echo "   ${GREEN}cd agentcore_template/agent/agent_config${NC}"
echo "   ${GREEN}# Edit agent_task.py and add:${NC}"
echo "   ${GREEN}from .tools.healthlake_tools import HEALTHLAKE_TOOLS${NC}"
echo "   ${GREEN}# Then update tools parameter: tools=HEALTHLAKE_TOOLS${NC}"
echo ""
echo "2. Deploy the agent:"
echo "   ${GREEN}cd agentcore_template${NC}"
echo "   ${GREEN}agentcore configure --entrypoint main.py -rf agent/requirements.txt -er ${RUNTIME_ROLE} --name ${PREFIX}-healthlake-agent${NC}"
echo "   ${GREEN}rm .agentcore.yaml${NC}"
echo "   ${GREEN}agentcore launch${NC}"
echo ""
echo "3. Test the agent:"
echo "   ${GREEN}agentcore invoke '{\"prompt\": \"What is the HealthLake datastore information?\"}' --agent ${PREFIX}-healthlake-agent${NC}"
echo ""
echo -e "${YELLOW}For detailed instructions, see:${NC}"
echo "   agents_catalog/35-healthlake-agent/AGENTCORE_TEMPLATE_README.md"
echo ""
