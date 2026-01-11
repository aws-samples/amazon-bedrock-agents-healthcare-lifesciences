#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

AWS="/usr/local/bin/aws"

print_header "Step 5: Create MCP Targets (2 Targets構成)"

cd "$(dirname "$SCRIPT_DIR")"

if [[ ! -f ".gateway-config" ]]; then
    print_error "Gateway configuration not found. Run 04_create_gateway.sh first"
    exit 1
fi

source .gateway-config

print_info "Gateway ID: $GATEWAY_ID"
print_info "Region: $REGION"

# ========================================
# Target 1: Bridge Container (5ツール)
# ========================================
print_step "Target 1: Bridge Container Target作成"

LAMBDA_ARN=$($AWS cloudformation describe-stacks \
  --stack-name sila2-lambda-proxy \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ProxyFunctionArn`].OutputValue' \
  --output text)

print_info "Lambda ARN: $LAMBDA_ARN"

# Lambda permission追加
$AWS lambda add-permission \
  --function-name sila2-mcp-proxy \
  --statement-id "BedrockAgentCore-${GATEWAY_ID}" \
  --action lambda:InvokeFunction \
  --principal bedrock-agentcore.amazonaws.com \
  --source-arn "$GATEWAY_ARN" \
  --region "$REGION" 2>/dev/null || print_info "Permission already exists"

# Target 1作成
TARGET1_ID=$(REGION="$REGION" GATEWAY_ID="$GATEWAY_ID" LAMBDA_ARN="$LAMBDA_ARN" ~/.pyenv/versions/3.10.12/bin/python3 << 'PYEOF'
import boto3
import os
import sys

try:
    client = boto3.client('bedrock-agentcore-control', region_name=os.environ['REGION'])
    response = client.create_gateway_target(
        gatewayIdentifier=os.environ['GATEWAY_ID'],
        name='sila2-bridge-container',
        description='SiLA2 Bridge Container (5 tools)',
        targetConfiguration={
            "mcp": {
                "lambda": {
                    "lambdaArn": os.environ['LAMBDA_ARN'],
                    "toolSchema": {
                        "inlinePayload": [
                            {
                                "name": "list_devices",
                                "description": "List all SiLA2 laboratory devices",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "device_type": {
                                            "type": "string",
                                            "description": "Optional filter by device type"
                                        }
                                    }
                                }
                            },
                            {
                                "name": "get_device_status",
                                "description": "Get device status",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "device_id": {
                                            "type": "string",
                                            "description": "Device identifier"
                                        }
                                    },
                                    "required": ["device_id"]
                                }
                            },
                            {
                                "name": "get_task_status",
                                "description": "Get task status and progress",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "task_id": {"type": "string", "description": "Task identifier"}
                                    },
                                    "required": ["task_id"]
                                }
                            },
                            {
                                "name": "get_property",
                                "description": "Get device property value (temperature, pressure, ph, etc)",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "device_id": {"type": "string", "description": "Device identifier"},
                                        "property_name": {"type": "string", "description": "Property name (e.g. temperature, pressure, ph)"}
                                    },
                                    "required": ["device_id", "property_name"]
                                }
                            },
                            {
                                "name": "execute_control",
                                "description": "Execute device control commands (set_temperature, abort_experiment)",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "device_id": {"type": "string", "description": "Device identifier"},
                                        "command": {"type": "string", "description": "Control command: set_temperature or abort_experiment"},
                                        "parameters": {"type": "object", "description": "Command parameters"}
                                    },
                                    "required": ["device_id", "command"]
                                }
                            }
                        ]
                    }
                }
            }
        },
        credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
    )
    print(response['targetId'])
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
)

if [[ $? -eq 0 ]]; then
    print_success "Target 1作成完了: $TARGET1_ID"
else
    print_error "Target 1作成失敗"
    exit 1
fi

# ========================================
# Target 2: sila2-analyze-heating-rate Lambda
# ========================================
print_step "Target 2: sila2-analyze-heating-rate Lambda作成"

# Lambda Role取得
LAMBDA_ROLE_ARN=$($AWS cloudformation describe-stacks \
  --stack-name sila2-lambda-proxy \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaRoleArn`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [[ -z "$LAMBDA_ROLE_ARN" ]]; then
    ACCOUNT_ID=$($AWS sts get-caller-identity --query Account --output text)
    LAMBDA_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/sila2-lambda-role"
fi

print_info "Lambda Role: $LAMBDA_ROLE_ARN"

# Lambda関数パッケージング
BUILD_DIR="build"
mkdir -p "$BUILD_DIR"

print_info "Packaging analyze-heating-rate..."
cd "lambda/tools/analyze_heating_rate"
zip -r "../../../$BUILD_DIR/analyze-heating-rate.zip" . -x "*.pyc" -x "__pycache__/*" >/dev/null 2>&1
cd "../../.."

# Lambda関数デプロイ
print_info "Deploying sila2-analyze-heating-rate Lambda..."
if $AWS lambda get-function --function-name "sila2-analyze-heating-rate" --region "$REGION" >/dev/null 2>&1; then
    $AWS lambda update-function-code \
        --function-name "sila2-analyze-heating-rate" \
        --zip-file "fileb://$BUILD_DIR/analyze-heating-rate.zip" \
        --region "$REGION" >/dev/null
    print_info "Updated analyze-heating-rate"
else
    $AWS lambda create-function \
        --function-name "sila2-analyze-heating-rate" \
        --runtime python3.11 \
        --handler index.lambda_handler \
        --role "$LAMBDA_ROLE_ARN" \
        --zip-file "fileb://$BUILD_DIR/analyze-heating-rate.zip" \
        --timeout 30 \
        --memory-size 256 \
        --region "$REGION" >/dev/null
    print_info "Created analyze-heating-rate"
fi

ANALYZE_LAMBDA_ARN=$($AWS lambda get-function \
  --function-name "sila2-analyze-heating-rate" \
  --region "$REGION" \
  --query 'Configuration.FunctionArn' \
  --output text)

print_info "Lambda ARN: $ANALYZE_LAMBDA_ARN"

# Lambda permission追加
$AWS lambda add-permission \
  --function-name analyze-heating-rate \
  --statement-id "BedrockAgentCore-${GATEWAY_ID}" \
  --action lambda:InvokeFunction \
  --principal bedrock-agentcore.amazonaws.com \
  --source-arn "$GATEWAY_ARN" \
  --region "$REGION" 2>/dev/null || print_info "Permission already exists"

# Target 2作成
TARGET2_ID=$(REGION="$REGION" GATEWAY_ID="$GATEWAY_ID" LAMBDA_ARN="$ANALYZE_LAMBDA_ARN" ~/.pyenv/versions/3.10.12/bin/python3 << 'PYEOF'
import boto3
import os
import sys

try:
    client = boto3.client('bedrock-agentcore-control', region_name=os.environ['REGION'])
    response = client.create_gateway_target(
        gatewayIdentifier=os.environ['GATEWAY_ID'],
        name='analyze-heating-rate',
        description='Heating rate analysis Lambda',
        targetConfiguration={
            "mcp": {
                "lambda": {
                    "lambdaArn": os.environ['LAMBDA_ARN'],
                    "toolSchema": {
                        "inlinePayload": [
                            {
                                "name": "analyze_heating_rate",
                                "description": "Calculate heating rate and detect anomalies",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "device_id": {"type": "string", "description": "Device identifier"},
                                        "history": {
                                            "type": "array",
                                            "description": "Temperature history data points",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "temperature": {"type": "number"},
                                                    "timestamp": {"type": "string"},
                                                    "scenario_mode": {"type": "string"}
                                                },
                                                "required": ["temperature", "timestamp"]
                                            }
                                        }
                                    },
                                    "required": ["device_id", "history"]
                                }
                            }
                        ]
                    }
                }
            }
        },
        credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
    )
    print(response['targetId'])
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
)

if [[ $? -eq 0 ]]; then
    print_success "Target 2作成完了: $TARGET2_ID"
else
    print_error "Target 2作成失敗"
    exit 1
fi

# ========================================
# 設定ファイル更新
# ========================================
print_step "設定ファイル更新"

cat >> .gateway-config << EOF
TARGET1_ID="$TARGET1_ID"
TARGET1_LAMBDA_ARN="$LAMBDA_ARN"
TARGET2_ID="$TARGET2_ID"
TARGET2_LAMBDA_ARN="$ANALYZE_LAMBDA_ARN"
EOF

print_success "MCP Targets作成完了"
print_info "Target 1 (Bridge Container): $TARGET1_ID"
print_info "Target 2 (analyze-heating-rate): $TARGET2_ID"
