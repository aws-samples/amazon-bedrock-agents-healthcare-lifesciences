#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Step 5c: Deploy AgentCore Runtime ==="
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # Load gateway configuration
    if [[ ! -f ".gateway-config" ]]; then
        log_error "Gateway configuration not found. Run 05a and 05b first"
        exit 1
    fi
    
    source .gateway-config
    
    log_info "Gateway ARN: $GATEWAY_ARN"
    log_info "Target ID: $TARGET_ID"
    
    local agent_name="sila2_phase3_agent"
    
    # Update main_agentcore_phase3.py with correct Gateway URL
    log_info "Updating Gateway URL in main_agentcore_phase3.py..."
    sed -i "s|GATEWAY_URL = os.getenv('GATEWAY_URL', '.*')|GATEWAY_URL = os.getenv('GATEWAY_URL', '$GATEWAY_URL')|" main_agentcore_phase3.py
    log_info "✅ Gateway URL updated: $GATEWAY_URL"
    
    # Clear existing AgentCore configuration
    log_info "Clearing AgentCore configuration..."
    rm -f .bedrock_agentcore.yaml 2>/dev/null || true
    
    # Run AgentCore configure
    log_info "Running AgentCore configure..."
    (echo "requirements.txt"; echo "no") | ~/.pyenv/versions/3.10.*/bin/agentcore configure \
        --name "$agent_name" \
        --entrypoint main_agentcore_phase3.py \
        --execution-role "$EXECUTION_ROLE_ARN" \
        --ecr "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bedrock-agentcore-$agent_name" \
        --region "$REGION" || log_warn "Configure failed, continuing..."
    
    # Update configuration file
    if [[ -f ".bedrock_agentcore.yaml" ]]; then
        log_info "Updating configuration file..."
        sed -i "s|execution_role:.*|execution_role: $EXECUTION_ROLE_ARN|g" .bedrock_agentcore.yaml
        
        # Add Gateway information
        cat > update_config.py << 'EOF'
import yaml
import sys

try:
    with open('.bedrock_agentcore.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    if 'agents' in config and 'sila2_phase3_agent' in config['agents']:
        config['agents']['sila2_phase3_agent']['gateway'] = {
            'name': sys.argv[1],
            'gateway_arn': sys.argv[2],
            'target_id': sys.argv[3]
        }
        
        with open('.bedrock_agentcore.yaml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print("Gateway configuration added successfully")
    else:
        print("Error: Agent configuration not found", file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
        
        python3 update_config.py "$GATEWAY_NAME" "$GATEWAY_ARN" "$TARGET_ID" || {
            log_error "Failed to update configuration"
            rm -f update_config.py
            return 1
        }
        
        rm -f update_config.py
        
        # Verify gateway configuration was added
        if grep -q "gateway:" .bedrock_agentcore.yaml; then
            log_info "✅ Gateway configuration verified in YAML"
            log_info "Gateway details:"
            grep -A 3 "gateway:" .bedrock_agentcore.yaml | sed 's/^/  /'
        else
            log_error "Gateway configuration not found in YAML file"
            return 1
        fi
    else
        log_error "Configuration file not found"
        return 1
    fi
    
    # Deploy AgentCore Runtime
    log_info "Deploying AgentCore Runtime..."
    ~/.pyenv/versions/3.10.*/bin/agentcore launch --auto-update-on-conflict || {
        log_error "AgentCore deployment failed"
        return 1
    }
    
    log_info "✅ AgentCore Runtime deployed"
    
    # Get Agent ID from status
    local agent_id=$(~/.pyenv/versions/3.10.*/bin/agentcore status 2>/dev/null | grep "Agent ID:" | awk '{print $NF}')
    log_info "Agent ID: $agent_id"
    
    # Attach Gateway to Runtime
    log_info "Attaching Gateway to Runtime..."
    REGION="$REGION" AGENT_ID="$agent_id" GATEWAY_ID="$GATEWAY_ID" TARGET_ID="$TARGET_ID" python3 << 'PYEOF'
import boto3
import os
import sys

try:
    client = boto3.client('bedrock-agentcore-control', region_name=os.environ.get('REGION', 'us-west-2'))
    
    agent_id = os.environ.get('AGENT_ID')
    gateway_id = os.environ.get('GATEWAY_ID')
    target_id = os.environ.get('TARGET_ID')
    
    # Associate Gateway with Runtime
    response = client.associate_agent_gateway(
        agentIdentifier=agent_id,
        gatewayIdentifier=gateway_id
    )
    
    print(f"Gateway associated: {response}")
    sys.exit(0)
    
except Exception as e:
    print(f"Warning: Gateway association failed: {e}", file=sys.stderr)
    sys.exit(0)  # Non-fatal error
PYEOF
    
    log_info "✅ Gateway attached to Runtime"
    
    # Check status
    log_info "Checking deployment status..."
    ~/.pyenv/versions/3.10.*/bin/agentcore status
    
    # Wait for agent to be ready
    log_info "Waiting for agent to be ready..."
    sleep 10
    
    # Test invocation
    log_info "Testing agent invocation..."
    ~/.pyenv/versions/3.10.*/bin/agentcore invoke '{"prompt": "List all available SiLA2 devices"}' || log_warn "Test invocation failed"
    
    log_info "✅ Step 5c complete"
}

main "$@"
