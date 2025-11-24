#!/bin/bash

# AgentCore Gateway デプロイ（Runtime手順を参考）
set -e

REGION="us-west-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
GATEWAY_NAME="sila2_gateway"
ECR_REPO_NAME="bedrock-agentcore-sila2-gateway"

echo "🚀 AgentCore Gateway デプロイ開始"
echo "📍 リージョン: $REGION"
echo "📍 アカウント: $ACCOUNT_ID"
echo "📍 Gateway名: $GATEWAY_NAME"

# Step 1: pyenv環境設定
echo "🐍 Step 1: pyenv環境設定..."
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv local 3.10.12

# Step 2: ECRリポジトリ作成
echo "🐳 Step 2: ECRリポジトリ作成..."
aws ecr create-repository \
  --repository-name $ECR_REPO_NAME \
  --region $REGION \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256 \
  2>/dev/null || echo "  ℹ️ ECRリポジトリは既に存在します"

# Step 3: Python仮想環境セットアップ
echo "🐍 Step 3: Python仮想環境セットアップ..."
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi

source .venv/bin/activate

# Step 4: 依存関係インストール
echo "📦 Step 4: 依存関係インストール..."
pip install --upgrade pip
pip install bedrock-agentcore

# Step 5: Gateway設定ファイル作成
echo "⚙️ Step 5: Gateway設定作成..."
cat > .bedrock_agentcore_gateway.yaml << EOF
agent_name: $GATEWAY_NAME
agent_description: "SiLA2 Lab Automation Gateway"
model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
region: $REGION
execution_role_arn: arn:aws:iam::$ACCOUNT_ID:role/sila2-lab-automation-phase3-complete-lambda-execution-role
ecr_repository: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME

tools:
  - name: list_devices
    description: "List all available SiLA2 devices"
    parameters:
      type: object
      properties: {}
  
  - name: device_status
    description: "Get status of a specific device"
    parameters:
      type: object
      properties:
        device_id:
          type: string
          description: "Device identifier"
      required: ["device_id"]
  
  - name: start_operation
    description: "Start operation on a device"
    parameters:
      type: object
      properties:
        device_id:
          type: string
          description: "Device identifier"
        operation:
          type: string
          description: "Operation to start"
      required: ["device_id", "operation"]

environment_variables:
  API_GATEWAY_URL: https://jn77k8pgyh.execute-api.us-west-2.amazonaws.com/dev
  ENVIRONMENT: dev
  GATEWAY_MODE: true
EOF

# Step 6: Gateway メインエントリーポイント作成
echo "📝 Step 6: Gateway メインエントリーポイント作成..."
cat > main_gateway.py << 'EOF'
"""
SiLA2 Lab Automation Gateway - AgentCore Gateway Entry Point
"""
import json
import os
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Gateway entry point for SiLA2 Lab Automation"""
    
    # Get environment variables
    api_gateway_url = os.environ.get('API_GATEWAY_URL')
    
    # Parse the request
    tool_name = event.get('tool_name', '')
    parameters = event.get('parameters', {})
    
    # Gateway tool routing
    if tool_name == 'list_devices':
        response = {
            'success': True,
            'devices': [
                {'id': 'HPLC-01', 'type': 'HPLC', 'status': 'ready', 'source': 'Gateway'},
                {'id': 'CENTRIFUGE-01', 'type': 'Centrifuge', 'status': 'idle', 'source': 'Gateway'},
                {'id': 'PIPETTE-01', 'type': 'Pipette', 'status': 'ready', 'source': 'Gateway'}
            ],
            'count': 3,
            'source': 'AgentCore Gateway'
        }
    elif tool_name == 'device_status':
        device_id = parameters.get('device_id', 'unknown')
        response = {
            'success': True,
            'device_id': device_id,
            'status': 'ready',
            'type': 'SiLA2 Device',
            'source': 'AgentCore Gateway'
        }
    elif tool_name == 'start_operation':
        device_id = parameters.get('device_id', 'unknown')
        operation = parameters.get('operation', 'default')
        response = {
            'success': True,
            'device_id': device_id,
            'operation': operation,
            'status': 'started',
            'source': 'AgentCore Gateway'
        }
    else:
        response = {
            'success': False,
            'error': f'Unknown tool: {tool_name}',
            'available_tools': ['list_devices', 'device_status', 'start_operation'],
            'source': 'AgentCore Gateway'
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
EOF

# Step 7: requirements.txt作成
echo "📋 Step 7: requirements.txt作成..."
cat > requirements_gateway.txt << 'EOF'
boto3>=1.26.0
requests>=2.28.0
pydantic>=1.10.0
EOF

# Step 8: AgentCore Gateway設定
echo "🔧 Step 8: AgentCore Gateway設定..."
echo "⏳ IAMロール伝播待機..."
sleep 30

# AgentCore configure for Gateway
echo "  AgentCore Gateway設定実行..."
LAMBDA_ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/sila2-lab-automation-phase3-complete-lambda-execution-role"
printf "$LAMBDA_ROLE_ARN\n\nrequirements_gateway.txt\nno\nno\n" | agentcore configure --entrypoint main_gateway.py --name $GATEWAY_NAME

# Step 9: AgentCore Gateway起動
echo "🚀 Step 9: AgentCore Gateway起動..."
agentcore launch

echo ""
echo "✅ AgentCore Gateway デプロイ完了!"
echo ""
echo "📋 デプロイ結果:"
echo "  Gateway Name: $GATEWAY_NAME"
echo "  Region: $REGION"
echo "  ECR Repository: $ECR_REPO_NAME"
echo ""
echo "🔍 AgentCoreコンソールで確認:"
echo "  https://console.aws.amazon.com/bedrock/home?region=$REGION#/agentcore"