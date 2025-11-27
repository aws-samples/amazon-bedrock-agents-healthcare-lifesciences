#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Phase 3 MCP-gRPC Bridge Setup (Fixed) ==="
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # Deploy improved MCP-gRPC Bridge Lambda
    deploy_mcp_bridge_lambda
    
    log_info "MCP-gRPC Bridge setup completed"
}

deploy_mcp_bridge_lambda() {
    log_info "Deploying MCP-gRPC Bridge Lambda (Gateway format)..."
    
    local function_name="mcp-grpc-bridge-dev"
    
    # Wait for any pending updates
    log_info "Checking Lambda function state..."
    local max_wait=60
    local waited=0
    while [ $waited -lt $max_wait ]; do
        local state=$(aws lambda get-function \
            --function-name "$function_name" \
            --region ${AWS_REGION:-us-west-2} \
            --query 'Configuration.LastUpdateStatus' \
            --output text 2>/dev/null || echo "NotFound")
        
        if [ "$state" = "Successful" ] || [ "$state" = "NotFound" ]; then
            break
        fi
        
        log_info "Waiting for function to be ready (state: $state)..."
        sleep 5
        waited=$((waited + 5))
    done
    
    # Use Gateway Lambda Target format
    if [ -f "mcp_grpc_bridge_lambda_gateway.py" ]; then
        cp mcp_grpc_bridge_lambda_gateway.py /tmp/lambda_function.py
    else
        log_error "mcp_grpc_bridge_lambda_gateway.py not found"
        exit 1
    fi
    
    # Create deployment package
    cd /tmp && zip -q lambda.zip lambda_function.py
    
    # Update function code
    aws lambda update-function-code \
        --function-name "$function_name" \
        --zip-file fileb://lambda.zip \
        --region ${AWS_REGION:-us-west-2} >/dev/null
    
    log_info "Waiting for code update to complete..."
    sleep 10
    
    # Update handler configuration
    aws lambda update-function-configuration \
        --function-name "$function_name" \
        --handler lambda_function.lambda_handler \
        --runtime python3.10 \
        --region ${AWS_REGION:-us-west-2} >/dev/null 2>&1 || log_warn "Configuration update skipped"
    
    log_info "MCP-gRPC Bridge Lambda (Gateway format) deployed successfully"
}

main "$@"