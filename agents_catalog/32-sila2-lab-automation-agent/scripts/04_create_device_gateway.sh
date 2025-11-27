#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Phase 3 Device API Gateway Setup ===" 
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # Create Device API Gateway
    create_device_api_gateway
    
    log_info "Device API Gateway created successfully"
}

create_device_api_gateway() {
    log_info "Creating Device API Gateway..."
    
    # Create API Gateway
    API_ID=$(aws apigateway create-rest-api \
        --name "sila2-device-api" \
        --description "SiLA2 Device API Gateway - Phase 3" \
        --query 'id' \
        --output text)
    
    log_info "API Gateway created: $API_ID"
    
    # Get root resource ID
    ROOT_ID=$(aws apigateway get-resources \
        --rest-api-id "$API_ID" \
        --query 'items[0].id' \
        --output text)
    
    # Create /devices resource
    DEVICES_ID=$(aws apigateway create-resource \
        --rest-api-id "$API_ID" \
        --parent-id "$ROOT_ID" \
        --path-part "devices" \
        --query 'id' \
        --output text)
    
    # Create /devices/{device_id} resource
    DEVICE_ID_RESOURCE=$(aws apigateway create-resource \
        --rest-api-id "$API_ID" \
        --parent-id "$DEVICES_ID" \
        --path-part "{device_id}" \
        --query 'id' \
        --output text)
    
    # Create /devices/{device_id}/execute resource
    EXECUTE_ID=$(aws apigateway create-resource \
        --rest-api-id "$API_ID" \
        --parent-id "$DEVICE_ID_RESOURCE" \
        --path-part "execute" \
        --query 'id' \
        --output text)
    
    # Get Lambda ARN (実際の関数名を使用)
    BRIDGE_ARN=$(aws lambda get-function \
        --function-name "mcp-grpc-bridge-dev" \
        --query 'Configuration.FunctionArn' \
        --output text)
    
    # Create methods and integrations
    create_api_method "$API_ID" "$DEVICES_ID" "GET" "list_devices" "$BRIDGE_ARN"
    create_api_method "$API_ID" "$DEVICE_ID_RESOURCE" "GET" "get_device_status" "$BRIDGE_ARN"  
    create_api_method "$API_ID" "$EXECUTE_ID" "POST" "execute_command" "$BRIDGE_ARN"
    
    # Deploy API
    aws apigateway create-deployment \
        --rest-api-id "$API_ID" \
        --stage-name "v1" \
        --description "Phase 3 deployment" >/dev/null
    
    # Get API endpoint
    REGION=$(aws configure get region)
    API_ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/v1"
    
    log_info "Device API Gateway deployed: $API_ENDPOINT"
    
    # Save configuration
    cat > ".device_api_config.json" << EOF
{
    "api_id": "$API_ID",
    "api_endpoint": "$API_ENDPOINT",
    "stage": "v1",
    "region": "$REGION"
}
EOF
}

create_api_method() {
    local api_id=$1
    local resource_id=$2
    local method=$3
    local tool_name=$4
    local lambda_arn=$5
    
    # Create method
    aws apigateway put-method \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method "$method" \
        --authorization-type "NONE" >/dev/null
    
    # Create integration
    aws apigateway put-integration \
        --rest-api-id "$api_id" \
        --resource-id "$resource_id" \
        --http-method "$method" \
        --type "AWS_PROXY" \
        --integration-http-method "POST" \
        --uri "arn:aws:apigateway:$(aws configure get region):lambda:path/2015-03-31/functions/$lambda_arn/invocations" >/dev/null
    
    # Add Lambda permission (実際の関数名を使用)
    aws lambda add-permission \
        --function-name "mcp-grpc-bridge-dev" \
        --statement-id "api-gateway-${resource_id}-${method}" \
        --action "lambda:InvokeFunction" \
        --principal "apigateway.amazonaws.com" \
        --source-arn "arn:aws:execute-api:$(aws configure get region):$(aws sts get-caller-identity --query Account --output text):${api_id}/*/${method}/*" 2>/dev/null || true
}

main "$@"