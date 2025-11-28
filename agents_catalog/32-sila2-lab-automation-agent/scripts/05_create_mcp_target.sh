#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

AWS="/usr/local/bin/aws"

print_header "Step 5: Create Lambda MCP Target"

cd "$(dirname "$SCRIPT_DIR")"

if [[ ! -f ".gateway-config" ]]; then
    print_error "Gateway configuration not found. Run 04_create_gateway.sh first"
    exit 1
fi

source .gateway-config

print_info "Gateway ID: $GATEWAY_ID"
print_info "Region: $REGION"

# Get Lambda ARN
print_step "Getting Lambda Proxy ARN"
LAMBDA_ARN=$($AWS cloudformation describe-stacks \
  --stack-name sila2-lambda-proxy \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ProxyFunctionArn`].OutputValue' \
  --output text)

print_info "Lambda ARN: $LAMBDA_ARN"

# Add Lambda permission
print_step "Adding Lambda permission for BedrockAgentCore"
$AWS lambda add-permission \
  --function-name sila2-mcp-proxy \
  --statement-id "BedrockAgentCore-${GATEWAY_ID}" \
  --action lambda:InvokeFunction \
  --principal bedrock-agentcore.amazonaws.com \
  --source-arn "$GATEWAY_ARN" \
  --region "$REGION" 2>/dev/null || print_info "Permission already exists"

# Create Gateway Target
print_step "Creating Lambda MCP Target"
TARGET_ID=$(REGION="$REGION" GATEWAY_ID="$GATEWAY_ID" LAMBDA_ARN="$LAMBDA_ARN" ~/.pyenv/versions/3.10.12/bin/python3 << 'PYEOF'
import boto3
import os
import sys

try:
    client = boto3.client('bedrock-agentcore-control', region_name=os.environ['REGION'])
    response = client.create_gateway_target(
        gatewayIdentifier=os.environ['GATEWAY_ID'],
        name='sila2-mcp-proxy',
        description='SiLA2 MCP Proxy via Lambda',
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
                                "name": "execute_command",
                                "description": "Execute device command",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "device_id": {"type": "string"},
                                        "command": {"type": "string"},
                                        "parameters": {"type": "object"}
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
    cat >> .gateway-config << EOF
TARGET_ID="$TARGET_ID"
LAMBDA_ARN="$LAMBDA_ARN"
EOF
    print_success "Lambda MCP Target created: $TARGET_ID"
    print_info "Lambda: $LAMBDA_ARN"
else
    print_error "Failed to create MCP Target"
    exit 1
fi
