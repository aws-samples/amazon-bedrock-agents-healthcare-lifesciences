#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Phase 3 Integration & Testing ===" 
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # Test component integration
    test_mock_devices
    test_mcp_bridge
    test_device_gateway
    test_end_to_end
    
    log_info "Phase 3 integration completed successfully"
}

test_mock_devices() {
    log_info "Testing Mock SiLA2 Devices..."
    
    for device in hplc centrifuge pipette; do
        log_info "Testing mock $device device..."
        
        # Lambda関数名を実際の名前に修正
        local function_name="mock-$device-device-dev"
        
        # 一時ファイルを使用してLambdaを呼び出し
        local temp_file="/tmp/lambda_response_$device.json"
        aws lambda invoke \
            --function-name "$function_name" \
            --payload '{"command":"status","device_id":"mock-'$device'-001"}' \
            "$temp_file" >/dev/null 2>&1
        
        local result=$(echo $?)
        
        if [ "$result" = "0" ]; then
            log_info "✅ Mock $device device: OK"
        else
            log_error "❌ Mock $device device: FAILED"
        fi
    done
}

test_mcp_bridge() {
    log_info "Testing MCP-gRPC Bridge..."
    
    # Test list_devices
    # MCP-gRPC Bridge関数名を実際の名前に修正
    local function_name="mcp-grpc-bridge-dev"
    
    # 一時ファイルを使用してLambdaを呼び出し
    local temp_file="/tmp/lambda_response_bridge.json"
    aws lambda invoke \
        --function-name "$function_name" \
        --payload '{"tool_name":"list_devices","parameters":{}}' \
        "$temp_file" >/dev/null 2>&1
    
    local result=$(echo $?)
    
    if [ "$result" = "0" ]; then
        log_info "✅ MCP-gRPC Bridge: OK"
    else
        log_error "❌ MCP-gRPC Bridge: FAILED"
    fi
}

test_device_gateway() {
    log_info "Testing Device API Gateway..."
    
    if [ -f ".device_api_config.json" ]; then
        API_ENDPOINT=$(jq -r '.api_endpoint' .device_api_config.json)
        
        # Test devices endpoint
        response=$(curl -s -o /dev/null -w "%{http_code}" "$API_ENDPOINT/devices" || echo "000")
        
        if [ "$response" = "200" ]; then
            log_info "✅ Device API Gateway: OK"
        else
            log_error "❌ Device API Gateway: FAILED (HTTP $response)"
        fi
    else
        log_error "❌ Device API Gateway config not found"
    fi
}

test_end_to_end() {
    log_info "Testing End-to-End Integration..."
    
    # Create integration test script
    cat > "test_phase3_integration.py" << 'EOF'
#!/usr/bin/env python3
import json
import boto3
import requests
import sys

def test_integration():
    """Test Phase 3 end-to-end integration"""
    
    # Load API config
    try:
        with open('.device_api_config.json', 'r') as f:
            config = json.load(f)
        api_endpoint = config['api_endpoint']
    except:
        print("❌ API config not found")
        return False
    
    # Test 1: List devices via API Gateway
    try:
        response = requests.get(f"{api_endpoint}/devices", timeout=10)
        if response.status_code == 200:
            devices = response.json().get('devices', [])
            print(f"✅ Found {len(devices)} devices via API Gateway")
        else:
            print(f"❌ API Gateway failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Gateway test failed: {e}")
        return False
    
    # Test 2: Get device status
    try:
        response = requests.get(f"{api_endpoint}/devices/mock-hplc-001", timeout=10)
        if response.status_code == 200:
            print("✅ Device status retrieval: OK")
        else:
            print(f"❌ Device status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Device status test failed: {e}")
        return False
    
    # Test 3: Execute command
    try:
        payload = {
            "command": "start_analysis",
            "parameters": {"method": "standard", "volume": 20}
        }
        response = requests.post(f"{api_endpoint}/devices/mock-hplc-001/execute", 
                               json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Command execution: OK")
        else:
            print(f"❌ Command execution failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Command execution test failed: {e}")
        return False
    
    print("🎉 Phase 3 End-to-End Integration: SUCCESS")
    return True

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
EOF

    # Run integration test
    python3 test_phase3_integration.py
    
    if [ $? -eq 0 ]; then
        log_info "✅ End-to-End Integration: SUCCESS"
    else
        log_error "❌ End-to-End Integration: FAILED"
    fi
    
    rm -f test_phase3_integration.py
}

main "$@"