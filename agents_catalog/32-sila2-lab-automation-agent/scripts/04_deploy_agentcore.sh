#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils/config.sh"
source "${SCRIPT_DIR}/utils/common.sh"

echo "=== AgentCore Deployment (Gateway + Memory + Runtime) ==="

# CFnから必要な情報を取得
EXECUTION_ROLE_ARN=$(get_stack_output "${MAIN_STACK_NAME}" "LambdaRoleArn")
PROXY_LAMBDA_ARN=$(get_stack_output "${MAIN_STACK_NAME}" "ProxyFunctionArn")
ANALYZE_LAMBDA_ARN=$(get_stack_output "${MAIN_STACK_NAME}" "AnalyzeHeatingRateFunctionArn")

echo "Execution Role: ${EXECUTION_ROLE_ARN}"
echo "Proxy Lambda: ${PROXY_LAMBDA_ARN}"
echo "Analyze Lambda: ${ANALYZE_LAMBDA_ARN}"

# ========================================
# Part 1: Gateway & Targets
# ========================================
echo ""
echo "=== Part 1: Gateway & Targets ==="

ROLE_NAME=$(echo $EXECUTION_ROLE_ARN | cut -d'/' -f2)
echo "Adding IAM permissions..."

/usr/local/bin/aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name BedrockAgentCoreAccess \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"bedrock-agentcore:*","Resource":"*"}]}' \
  --region "${DEFAULT_REGION}" 2>/dev/null || echo "Permission already exists"

/usr/local/bin/aws iam update-assume-role-policy --role-name "$ROLE_NAME" \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":["lambda.amazonaws.com","bedrock-agentcore.amazonaws.com","codebuild.amazonaws.com"]},"Action":"sts:AssumeRole"}]}' \
  --region "${DEFAULT_REGION}"

echo "✅ IAM permissions updated"

# Add S3 permissions for CodeBuild
echo "Adding S3 permissions for CodeBuild..."
S3_BUCKET="bedrock-agentcore-codebuild-sources-${ACCOUNT_ID}-${DEFAULT_REGION}"

cat > /tmp/s3-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::$S3_BUCKET",
        "arn:aws:s3:::$S3_BUCKET/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

/usr/local/bin/aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "CodeBuildS3Access" \
    --policy-document file:///tmp/s3-policy.json \
    --region "${DEFAULT_REGION}" 2>/dev/null || echo "S3 policy already exists"

rm -f /tmp/s3-policy.json
echo "✅ S3 permissions added"

# Add CodeBuild trust policy
echo "Adding CodeBuild trust policy..."
/usr/local/bin/aws iam get-role --role-name "$ROLE_NAME" --region "${DEFAULT_REGION}" --query 'Role.AssumeRolePolicyDocument' > /tmp/trust-policy.json

if ! grep -q "codebuild.amazonaws.com" /tmp/trust-policy.json; then
    ~/.pyenv/versions/3.10.12/bin/python3 << 'PYEOF'
import json
with open('/tmp/trust-policy.json', 'r') as f:
    policy = json.load(f)
for statement in policy['Statement']:
    if statement.get('Effect') == 'Allow' and 'Service' in statement.get('Principal', {}):
        services = statement['Principal']['Service']
        if isinstance(services, str):
            services = [services]
        if 'codebuild.amazonaws.com' not in services:
            services.append('codebuild.amazonaws.com')
        statement['Principal']['Service'] = services
        break
with open('/tmp/trust-policy-updated.json', 'w') as f:
    json.dump(policy, f, indent=2)
PYEOF
    /usr/local/bin/aws iam update-assume-role-policy --role-name "$ROLE_NAME" --policy-document file:///tmp/trust-policy-updated.json --region "${DEFAULT_REGION}"
    rm -f /tmp/trust-policy.json /tmp/trust-policy-updated.json
    echo "✅ CodeBuild trust policy added"
else
    rm -f /tmp/trust-policy.json
    echo "✅ CodeBuild trust policy exists"
fi

# Add Lambda Invoke permissions
echo "Adding Lambda Invoke permissions..."
cat > /tmp/lambda-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:${DEFAULT_REGION}:${ACCOUNT_ID}:function:sila2-mcp-proxy",
        "arn:aws:lambda:${DEFAULT_REGION}:${ACCOUNT_ID}:function:sila2-analyze-heating-rate"
      ]
    }
  ]
}
EOF
/usr/local/bin/aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "LambdaInvokePolicy" --policy-document file:///tmp/lambda-policy.json --region "${DEFAULT_REGION}" 2>/dev/null || echo "Lambda policy exists"
rm -f /tmp/lambda-policy.json
echo "✅ Lambda Invoke permissions added"

# Add Memory permissions
echo "Adding Memory permissions..."
cat > /tmp/memory-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateEvent",
        "bedrock-agentcore:GetMemory",
        "bedrock-agentcore:ListMemories",
        "bedrock-agentcore:RetrieveMemory"
      ],
      "Resource": "arn:aws:bedrock-agentcore:${DEFAULT_REGION}:${ACCOUNT_ID}:memory/*"
    }
  ]
}
EOF
/usr/local/bin/aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "BedrockAgentCoreMemoryPolicy" --policy-document file:///tmp/memory-policy.json --region "${DEFAULT_REGION}" 2>/dev/null || echo "Memory policy exists"
rm -f /tmp/memory-policy.json
echo "✅ Memory permissions added"

# Gateway作成
GATEWAY_NAME="sila2-gateway-$(date +%s)"
echo "Creating Gateway: ${GATEWAY_NAME}..."

GATEWAY_OUTPUT=$(~/.pyenv/versions/3.10.12/bin/python3 << PYEOF
import boto3
client = boto3.client('bedrock-agentcore-control', region_name='${DEFAULT_REGION}')
r = client.create_gateway(
    name='${GATEWAY_NAME}',
    roleArn='${EXECUTION_ROLE_ARN}',
    protocolType='MCP',
    authorizerType='AWS_IAM',
    description='SiLA2 Lab Automation Gateway'
)
print(f"{r['gatewayId']}|{r['gatewayArn']}|{r['gatewayUrl']}")
PYEOF
)

IFS='|' read -r GATEWAY_ID GATEWAY_ARN GATEWAY_URL <<< "$GATEWAY_OUTPUT"
echo "✅ Gateway created"
echo "  ID: ${GATEWAY_ID}"
echo "  ARN: ${GATEWAY_ARN}"
echo "  URL: ${GATEWAY_URL}"

# Lambda権限追加
echo "Adding Lambda permissions..."
/usr/local/bin/aws lambda add-permission --function-name sila2-mcp-proxy \
  --statement-id "BedrockAgentCore-${GATEWAY_ID}" --action lambda:InvokeFunction \
  --principal bedrock-agentcore.amazonaws.com --source-arn "$GATEWAY_ARN" \
  --region "${DEFAULT_REGION}" 2>/dev/null || echo "Permission already exists"

# Target 1: Bridge Container
echo "Creating Target 1: Bridge Container..."
TARGET1_ID=$(~/.pyenv/versions/3.10.12/bin/python3 << PYEOF
import boto3
client = boto3.client('bedrock-agentcore-control', region_name='${DEFAULT_REGION}')
r = client.create_gateway_target(
    gatewayIdentifier='${GATEWAY_ID}',
    name='sila2-bridge-container',
    description='SiLA2 Bridge Container (5 tools)',
    targetConfiguration={'mcp':{'lambda':{'lambdaArn':'${PROXY_LAMBDA_ARN}','toolSchema':{'inlinePayload':[
        {'name':'list_devices','description':'List all SiLA2 devices','inputSchema':{'type':'object','properties':{'device_type':{'type':'string'}}}},
        {'name':'get_device_status','description':'Get device status','inputSchema':{'type':'object','properties':{'device_id':{'type':'string'}},'required':['device_id']}},
        {'name':'get_task_status','description':'Get task status','inputSchema':{'type':'object','properties':{'task_id':{'type':'string'}},'required':['task_id']}},
        {'name':'get_property','description':'Get device property','inputSchema':{'type':'object','properties':{'device_id':{'type':'string'},'property_name':{'type':'string'}},'required':['device_id','property_name']}},
        {'name':'execute_control','description':'Execute control command','inputSchema':{'type':'object','properties':{'device_id':{'type':'string'},'command':{'type':'string'},'parameters':{'type':'object'}},'required':['device_id','command']}}
    ]}}}},
    credentialProviderConfigurations=[{'credentialProviderType':'GATEWAY_IAM_ROLE'}]
)
print(r['targetId'])
PYEOF
)

echo "✅ Target 1 created: ${TARGET1_ID}"

# Target 2: Analyze Heating Rate
echo "Creating Target 2: Analyze Heating Rate..."
/usr/local/bin/aws lambda add-permission --function-name sila2-analyze-heating-rate \
  --statement-id "BedrockAgentCore-${GATEWAY_ID}" --action lambda:InvokeFunction \
  --principal bedrock-agentcore.amazonaws.com --source-arn "$GATEWAY_ARN" \
  --region "${DEFAULT_REGION}" 2>/dev/null || echo "Permission already exists"

TARGET2_ID=$(~/.pyenv/versions/3.10.12/bin/python3 << PYEOF
import boto3
client = boto3.client('bedrock-agentcore-control', region_name='${DEFAULT_REGION}')
r = client.create_gateway_target(
    gatewayIdentifier='${GATEWAY_ID}',
    name='analyze-heating-rate',
    description='Heating rate analysis Lambda',
    targetConfiguration={'mcp':{'lambda':{'lambdaArn':'${ANALYZE_LAMBDA_ARN}','toolSchema':{'inlinePayload':[
        {'name':'analyze_heating_rate','description':'Calculate heating rate and detect anomalies','inputSchema':{'type':'object','properties':{'device_id':{'type':'string'},'history':{'type':'array','items':{'type':'object','properties':{'temperature':{'type':'number'},'timestamp':{'type':'string'}}}}},'required':['device_id','history']}}
    ]}}}},
    credentialProviderConfigurations=[{'credentialProviderType':'GATEWAY_IAM_ROLE'}]
)
print(r['targetId'])
PYEOF
)

echo "✅ Target 2 created: ${TARGET2_ID}"

# ========================================
# Part 2: Memory
# ========================================
echo ""
echo "=== Part 2: Memory ==="

MEMORY_ID=$(~/.pyenv/versions/3.10.12/bin/python3 << PYEOF
import boto3
client = boto3.client('bedrock-agentcore-control', region_name='${DEFAULT_REGION}')
try:
    memories = client.list_memories()
    for m in memories.get('memories', []):
        if 'sila2_memory' in m.get('id', ''):
            print(m['id'])
            exit(0)
except:
    pass
print('')
PYEOF
)

if [ -z "$MEMORY_ID" ]; then
    echo "Creating Memory..."
    ~/.pyenv/versions/3.10.12/bin/agentcore memory create sila2_memory \
        --region "${DEFAULT_REGION}" \
        --description "SiLA2 device control memory" \
        --strategies '[{"summaryMemoryStrategy":{"name":"DeviceControlSummary","description":"Summarizes device control decisions","namespaces":["/summaries/{actorId}/{sessionId}"]}}]' \
        --wait
    
    sleep 5
    
    MEMORY_ID=$(/usr/local/bin/aws bedrock-agentcore-control list-memories \
        --region "${DEFAULT_REGION}" \
        --query "memories[?starts_with(id, 'sila2_memory')].id | [0]" \
        --output text)
fi

echo "✅ Memory ID: ${MEMORY_ID}"

# ========================================
# Part 3: Runtime
# ========================================
echo ""
echo "=== Part 3: Runtime ==="

AGENT_NAME="sila2_agent"

# ECR作成
create_ecr_if_not_exists "bedrock-agentcore-${AGENT_NAME}"

# Gateway URL更新
cd "$(dirname "$SCRIPT_DIR")"
sed -i "s|GATEWAY_URL = os.getenv('GATEWAY_URL', '.*')|GATEWAY_URL = os.getenv('GATEWAY_URL', '$GATEWAY_URL')|" main_agentcore.py

# Configure
rm -f .bedrock_agentcore.yaml
~/.pyenv/versions/3.10.12/bin/agentcore configure \
    --name "${AGENT_NAME}" \
    --entrypoint main_agentcore.py \
    --execution-role "${EXECUTION_ROLE_ARN}" \
    --code-build-execution-role "${EXECUTION_ROLE_ARN}" \
    --ecr "${ACCOUNT_ID}.dkr.ecr.${DEFAULT_REGION}.amazonaws.com/bedrock-agentcore-${AGENT_NAME}" \
    --region "${DEFAULT_REGION}" \
    --requirements-file requirements.txt \
    --disable-memory \
    --non-interactive

# Update config with Gateway and Memory
~/.pyenv/versions/3.10.12/bin/python3 << PYEOF
import yaml
with open('.bedrock_agentcore.yaml', 'r') as f:
    config = yaml.safe_load(f)
if 'agents' in config and '${AGENT_NAME}' in config['agents']:
    config['agents']['${AGENT_NAME}']['gateway'] = {
        'name': '${GATEWAY_NAME}',
        'gateway_arn': '${GATEWAY_ARN}',
        'target_id': '${TARGET1_ID}'
    }
    config['agents']['${AGENT_NAME}']['memory'] = {
        'mode': 'STM_AND_LTM',
        'memory_id': '${MEMORY_ID}',
        'memory_arn': 'arn:aws:bedrock-agentcore:${DEFAULT_REGION}:${ACCOUNT_ID}:memory/${MEMORY_ID}',
        'memory_name': 'sila2_memory'
    }
    with open('.bedrock_agentcore.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
PYEOF

# Deploy
echo "Deploying Runtime..."
~/.pyenv/versions/3.10.12/bin/agentcore deploy --auto-update-on-conflict

AGENT_ARN=$(~/.pyenv/versions/3.10.12/bin/agentcore status 2>/dev/null | grep "Agent ARN:" | awk '{print $NF}')
AGENT_ID=$(echo "$AGENT_ARN" | awk -F'/' '{print $NF}')

echo "✅ Runtime deployed"
echo "  Agent ID: ${AGENT_ID}"
echo "  Agent ARN: ${AGENT_ARN}"

# Associate Gateway
~/.pyenv/versions/3.10.12/bin/python3 << PYEOF
import boto3
client = boto3.client('bedrock-agentcore-control', region_name='${DEFAULT_REGION}')
try:
    client.associate_agent_gateway(
        agentIdentifier='${AGENT_ID}',
        gatewayIdentifier='${GATEWAY_ID}'
    )
    print("✅ Gateway associated")
except Exception as e:
    print(f"Warning: {e}")
PYEOF

# 設定ファイル保存
cat > "${SCRIPT_DIR}/../.gateway-config" << EOF
GATEWAY_ID="${GATEWAY_ID}"
GATEWAY_ARN="${GATEWAY_ARN}"
GATEWAY_URL="${GATEWAY_URL}"
TARGET1_ID="${TARGET1_ID}"
TARGET2_ID="${TARGET2_ID}"
MEMORY_ID="${MEMORY_ID}"
AGENT_ID="${AGENT_ID}"
AGENT_ARN="${AGENT_ARN}"
EOF

# Lambda環境変数を更新
echo ""
echo "=== Updating Lambda Environment Variables ==="

RUNTIME_ARN=$(~/.pyenv/versions/3.10.12/bin/agentcore status 2>/dev/null | grep "Runtime ARN:" | awk '{print $NF}')

echo "Updating sila2-agentcore-invoker..."
/usr/local/bin/aws lambda update-function-configuration \
  --function-name sila2-agentcore-invoker \
  --environment "Variables={BRIDGE_SERVER_URL=http://bridge.sila2.local:8080,AGENTCORE_RUNTIME_ARN=${RUNTIME_ARN},AGENTCORE_MEMORY_ID=${MEMORY_ID}}" \
  --region "${DEFAULT_REGION}" \
  --query 'LastModified' \
  --output text && echo "✅ Lambda environment variables updated"

echo "Waiting for Lambda configuration to propagate..."
sleep 5

echo ""
echo "=== Deployment Complete ==="
echo "Gateway ID: ${GATEWAY_ID}"
echo "Memory ID: ${MEMORY_ID}"
echo "Agent ID: ${AGENT_ID}"
echo "Runtime ARN: ${RUNTIME_ARN}"
echo ""
echo "Configuration saved to .gateway-config"
