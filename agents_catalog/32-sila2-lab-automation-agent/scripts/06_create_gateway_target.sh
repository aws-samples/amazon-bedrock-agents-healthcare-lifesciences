#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Step 5b: Create Gateway Target (boto3) ==="
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # Load gateway configuration
    if [[ ! -f ".gateway-config" ]]; then
        log_error "Gateway configuration not found. Run 05a_create_gateway.sh first"
        exit 1
    fi
    
    source .gateway-config
    
    # Extract full gateway identifier from GATEWAY_URL or use GATEWAY_NAME with suffix
    if [[ -n "$GATEWAY_URL" ]]; then
        GATEWAY_IDENTIFIER=$(echo "$GATEWAY_URL" | sed -n 's|https://\([^.]*\)\.gateway\..*|\1|p')
    else
        log_error "GATEWAY_URL not found in configuration"
        exit 1
    fi
    
    log_info "Gateway Identifier: $GATEWAY_IDENTIFIER"
    log_info "Region: $REGION"
    
    # Get Lambda ARN
    local mcp_bridge_arn="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:mcp-grpc-bridge-dev"
    log_info "Lambda ARN: $mcp_bridge_arn"
    
    # Add Lambda permission
    log_info "Adding Lambda permission..."
    aws lambda add-permission \
        --function-name mcp-grpc-bridge-dev \
        --statement-id "BedrockAgentCore-${GATEWAY_ID}" \
        --action lambda:InvokeFunction \
        --principal bedrock-agentcore.amazonaws.com \
        --source-arn "$GATEWAY_ARN" \
        --region "$REGION" 2>/dev/null || log_info "Permission already exists"
    
    # Create Gateway Target using Python boto3
    log_info "Creating Gateway Target with boto3..."
    
    local target_output=$(REGION="$REGION" GATEWAY_IDENTIFIER="$GATEWAY_IDENTIFIER" mcp_bridge_arn="$mcp_bridge_arn" ~/.pyenv/versions/3.10.12/bin/python3 << 'PYEOF'
import boto3
import json
import sys
import os

try:
    client = boto3.client('bedrock-agentcore-control', region_name=os.environ.get('REGION', 'us-west-2'))
    
    gateway_identifier = os.environ.get('GATEWAY_IDENTIFIER')
    lambda_arn = os.environ.get('mcp_bridge_arn')
    
    lambda_target_config = {
        "mcp": {
            "lambda": {
                "lambdaArn": lambda_arn,
                "toolSchema": {
                    "inlinePayload": [
                        {
                            "name": "list_devices",
                            "description": "List all available SiLA2 laboratory devices",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "device_type": {
                                        "type": "string",
                                        "description": "Optional filter by device type (hplc, centrifuge, pipette)"
                                    }
                                }
                            }
                        },
                        {
                            "name": "get_device_status",
                            "description": "Get the current status of a specific SiLA2 device",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "device_id": {
                                        "type": "string",
                                        "description": "Device identifier (e.g., mock-hplc-001)"
                                    }
                                },
                                "required": ["device_id"]
                            }
                        },
                        {
                            "name": "execute_command",
                            "description": "Execute a command on a SiLA2 device",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "device_id": {
                                        "type": "string",
                                        "description": "Device identifier"
                                    },
                                    "command": {
                                        "type": "string",
                                        "description": "Command to execute (e.g., start_analysis, stop, get_results)"
                                    },
                                    "parameters": {
                                        "type": "object",
                                        "description": "Command-specific parameters"
                                    }
                                },
                                "required": ["device_id", "command"]
                            }
                        }
                    ]
                }
            }
        }
    }
    
    credential_config = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
    
    response = client.create_gateway_target(
        gatewayIdentifier=gateway_identifier,
        name="mcp-grpc-bridge-target",
        description="MCP gRPC Bridge Lambda Target",
        targetConfiguration=lambda_target_config,
        credentialProviderConfigurations=credential_config
    )
    
    print(response['targetId'])
    sys.exit(0)
    
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
)
    
    if [[ $? -eq 0 ]]; then
        # Append to configuration
        cat >> .gateway-config << EOF
TARGET_ID="$target_output"
MCP_BRIDGE_ARN="$mcp_bridge_arn"
EOF
        
        log_info "✅ Gateway Target created: $target_output"
    else
        log_error "Gateway Target creation failed"
        exit 1
    fi
}

main "$@"
