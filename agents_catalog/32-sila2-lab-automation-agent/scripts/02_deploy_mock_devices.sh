#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Phase 3 Mock SiLA2 Device Deployment (Fixed) ===" 
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # Create gRPC Layer first
    create_grpc_layer
    
    # Create Mock Device Lambdas with gRPC support
    create_mock_hplc_lambda
    sleep 15
    create_mock_device_lambda "centrifuge" "Mock Centrifuge SiLA2 Device"
    sleep 15
    create_mock_device_lambda "pipette" "Mock Pipette SiLA2 Device"
    
    log_info "Mock SiLA2 devices deployed successfully"
}

create_grpc_layer() {
    log_info "Creating gRPC Layer for Python 3.10..."
    
    # Clean and create layer directory
    rm -rf /tmp/layer && mkdir -p /tmp/layer/python
    
    # Install gRPC libraries
    pip install grpcio protobuf -t /tmp/layer/python/
    
    # Create layer package
    cd /tmp/layer && zip -r grpc-layer-v2.zip python/
    
    # Create or update layer
    LAYER_ARN=$(aws lambda publish-layer-version \
        --layer-name grpc-layer-v2 \
        --zip-file fileb://grpc-layer-v2.zip \
        --compatible-runtimes python3.10 \
        --region ${AWS_REGION:-us-west-2} \
        --query 'LayerVersionArn' --output text 2>/dev/null || echo "")
    
    if [ -z "$LAYER_ARN" ]; then
        # Try to get existing layer
        LAYER_ARN=$(aws lambda list-layer-versions \
            --layer-name grpc-layer-v2 \
            --region ${AWS_REGION:-us-west-2} \
            --query 'LayerVersions[0].LayerVersionArn' --output text 2>/dev/null || echo "")
    fi
    
    log_info "gRPC Layer ARN: $LAYER_ARN"
    export GRPC_LAYER_ARN="$LAYER_ARN"
}

create_mock_hplc_lambda() {
    create_mock_device_lambda "hplc" "Mock HPLC SiLA2 Device"
}

create_mock_device_lambda() {
    local device_type=$1
    local description=$2
    local function_name="mock-${device_type}-device-dev"
    
    log_info "Creating Mock $device_type Lambda..."
    
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
    
    # Create simplified Lambda function code
    cat > "/tmp/mock_${device_type}_lambda.py" << EOF
import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Mock SiLA2 $device_type device simulator"""
    
    try:
        action = event.get('action', 'get_status')
        device_id = event.get('device_id', 'mock-${device_type}-001')
        
        if action == 'get_status':
            result = {
                'device_id': device_id,
                'device_type': '$device_type',
                'status': 'ready',
                'capabilities': get_${device_type}_capabilities(),
                'timestamp': datetime.now().isoformat(),
                'sila2_compliant': True
            }
        elif action == 'start_analysis' or action.startswith('execute'):
            parameters = event.get('parameters', {})
            result = {
                'device_id': device_id,
                'operation': action,
                'success': True,
                'status': 'completed',
                'result': execute_${device_type}_command(parameters),
                'timestamp': datetime.now().isoformat(),
                'sila2_compliant': True
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unsupported action: {action}'})
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'result': result,
                'device_type': '$device_type'
            })
        }
        
    except Exception as e:
        logger.error(f"$device_type Lambda error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_${device_type}_capabilities():
    """Return device-specific capabilities"""
    capabilities = {
        'centrifuge': ['set_speed', 'start_spin', 'stop_spin', 'get_status'],
        'pipette': ['aspirate', 'dispense', 'set_volume', 'get_status']
    }
    return capabilities.get('$device_type', ['get_status'])

def execute_${device_type}_command(parameters):
    """Execute device-specific command"""
    return {
        'estimated_time': 300,
        'executed_parameters': parameters,
        'run_id': f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }
EOF

    # Create deployment package
    cd /tmp && zip lambda.zip "mock_${device_type}_lambda.py"
    
    # Deploy Lambda
    local function_name="mock-${device_type}-device-dev"
    
    # Update function code
    aws lambda update-function-code \
        --function-name "$function_name" \
        --zip-file fileb://lambda.zip \
        --region ${AWS_REGION:-us-west-2} >/dev/null
    
    # Wait for code update to complete
    log_info "Waiting for code update to complete..."
    sleep 10
    
    # Update runtime to Python 3.10
    aws lambda update-function-configuration \
        --function-name "$function_name" \
        --runtime python3.10 \
        --handler "mock_${device_type}_lambda.lambda_handler" \
        --region ${AWS_REGION:-us-west-2} >/dev/null 2>&1 || log_warn "Configuration update skipped (may be in progress)"
    
    rm "/tmp/mock_${device_type}_lambda.py"
    
    log_info "Mock $device_type Lambda deployed"
}

main "$@"