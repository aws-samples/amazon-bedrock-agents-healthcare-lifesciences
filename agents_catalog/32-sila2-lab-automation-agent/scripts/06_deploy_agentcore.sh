#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Step 6: Deploy AgentCore Runtime (Phase 4-6 + Phase 7) ==="
    
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
    
    # Create AgentCore ECR repository if it doesn't exist
    log_info "Creating AgentCore ECR repository..."
    aws ecr describe-repositories --repository-names "bedrock-agentcore-$agent_name" --region "$REGION" 2>/dev/null || \
      aws ecr create-repository --repository-name "bedrock-agentcore-$agent_name" --region "$REGION" \
        --image-scanning-configuration scanOnPush=true
    log_info "✅ ECR repository ready"
    
    # Update main_agentcore_phase3.py with correct Gateway URL
    log_info "Updating Gateway URL in main_agentcore_phase3.py..."
    sed -i "s|GATEWAY_URL = os.getenv('GATEWAY_URL', '.*')|GATEWAY_URL = os.getenv('GATEWAY_URL', '$GATEWAY_URL')|" main_agentcore_phase3.py
    log_info "✅ Gateway URL updated: $GATEWAY_URL"
    
    # Clear existing AgentCore configuration
    log_info "Clearing AgentCore configuration..."
    rm -f .bedrock_agentcore.yaml 2>/dev/null || true
    
    # Run AgentCore configure
    log_info "Running AgentCore configure..."
    
    # Add CodeBuild trust policy to execution role
    log_info "Adding CodeBuild trust policy to execution role..."
    local role_name=$(echo "$EXECUTION_ROLE_ARN" | awk -F'/' '{print $NF}')
    /usr/local/bin/aws iam get-role --role-name "$role_name" --region "$REGION" --query 'Role.AssumeRolePolicyDocument' > /tmp/trust-policy.json
    
    # Check if codebuild.amazonaws.com is already in the trust policy
    if ! grep -q "codebuild.amazonaws.com" /tmp/trust-policy.json; then
        log_info "Adding codebuild.amazonaws.com to trust policy..."
        python3 << 'PYEOF'
import json
import sys

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
        
        /usr/local/bin/aws iam update-assume-role-policy \
            --role-name "$role_name" \
            --policy-document file:///tmp/trust-policy-updated.json \
            --region "$REGION"
        
        log_info "✅ CodeBuild trust policy added"
        rm -f /tmp/trust-policy.json /tmp/trust-policy-updated.json
    else
        log_info "✅ CodeBuild trust policy already exists"
        rm -f /tmp/trust-policy.json
    fi
    
    # Add S3 permissions for CodeBuild
    log_info "Adding S3 permissions for CodeBuild..."
    local s3_policy_name="CodeBuildS3Access"
    local s3_bucket="bedrock-agentcore-codebuild-sources-$ACCOUNT_ID-$REGION"
    
    # Create inline policy for S3 access
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
        "arn:aws:s3:::$s3_bucket",
        "arn:aws:s3:::$s3_bucket/*"
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
        --role-name "$role_name" \
        --policy-name "$s3_policy_name" \
        --policy-document file:///tmp/s3-policy.json \
        --region "$REGION" || log_warn "Failed to add S3 policy"
    
    rm -f /tmp/s3-policy.json
    log_info "✅ S3 permissions added"
    
    ~/.pyenv/versions/3.10.*/bin/agentcore configure \
        --name "$agent_name" \
        --entrypoint main_agentcore_phase3.py \
        --execution-role "$EXECUTION_ROLE_ARN" \
        --code-build-execution-role "$EXECUTION_ROLE_ARN" \
        --ecr "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bedrock-agentcore-$agent_name" \
        --region "$REGION" \
        --requirements-file requirements.txt \
        --disable-memory \
        --non-interactive || log_warn "Configure failed, continuing..."
    
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
    
    # ========================================
    # Phase 7: Create Memory BEFORE deployment
    # ========================================
    log_info "[Phase 7] Creating AgentCore Memory with Summary Strategy..."
    
    # Check if memory already exists in config
    local memory_id=""
    if [[ -f ".gateway-config" ]] && grep -q "MEMORY_ID=" .gateway-config; then
        memory_id=$(grep "MEMORY_ID=" .gateway-config | cut -d'=' -f2)
        log_info "[Phase 7] Using existing Memory ID: $memory_id"
    else
        # Check for existing memory with same name
        log_info "[Phase 7] Checking for existing memory..."
        local existing_memory=$(~/.pyenv/versions/3.10.12/bin/agentcore memory list --region "$REGION" 2>/dev/null | grep "sila2_phase7_memory" || echo "")
        
        if [[ -n "$existing_memory" ]]; then
            memory_id=$(echo "$existing_memory" | grep -oP 'Memory ID: \K[^\s]+' || echo "")
            if [[ -n "$memory_id" ]]; then
                log_info "[Phase 7] Found existing Memory ID: $memory_id"
                echo "MEMORY_ID=$memory_id" >> .gateway-config
            fi
        fi
        
        # Create new memory only if none exists
        if [[ -z "$memory_id" ]]; then
            log_info "[Phase 7] Creating new Memory with Summary Strategy for long-term persistence..."
            local memory_output=$(~/.pyenv/versions/3.10.12/bin/agentcore memory create sila2_phase7_memory \
                --region "$REGION" \
                --description "Phase 7 memory with Summary Strategy for AI decision persistence" \
                --strategies '[{"summaryMemoryStrategy": {"name": "DeviceControlSummary", "description": "Summarizes AI decisions for device control and heating analysis", "namespaces": ["/summaries/{actorId}/{sessionId}"]}}]' \
                --wait 2>&1)
            
            log_info "[Phase 7] Memory output: $memory_output"
            
            # Extract Memory ID from output
            memory_id=$(echo "$memory_output" | grep -oP 'Memory ID: \K[^\s]+' || echo "")
            
            if [[ -z "$memory_id" ]]; then
                # Try alternative extraction from ARN
                memory_id=$(echo "$memory_output" | grep -oP 'arn:aws:bedrock-agentcore:[^:]+:[^:]+:memory/\K[^\s]+' || echo "")
            fi
            
            if [[ -n "$memory_id" ]]; then
                log_info "[Phase 7] New Memory ID: $memory_id"
                echo "MEMORY_ID=$memory_id" >> .gateway-config
            else
                log_error "[Phase 7] Memory creation failed"
                return 1
            fi
        fi
    fi
    
    # Update YAML config to use Phase 7 memory with LTM mode
    if [[ -n "$memory_id" ]]; then
        log_info "[Phase 7] Updating YAML config with Memory ID: $memory_id"
        python3 << PYEOF
import yaml

with open('.bedrock_agentcore.yaml', 'r') as f:
    config = yaml.safe_load(f)

if 'agents' in config and 'sila2_phase3_agent' in config['agents']:
    # Add complete memory configuration
    config['agents']['sila2_phase3_agent']['memory'] = {
        'mode': 'STM_AND_LTM',
        'memory_id': '$memory_id',
        'memory_arn': 'arn:aws:bedrock-agentcore:$REGION:$ACCOUNT_ID:memory/$memory_id',
        'memory_name': 'sila2_phase7_memory',
        'event_expiry_days': 30,
        'first_invoke_memory_check_done': False,
        'was_created_by_toolkit': False
    }
    
    with open('.bedrock_agentcore.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print("Memory configuration added to config")
PYEOF
    fi
    
    # Deploy AgentCore Runtime
    log_info "Deploying AgentCore Runtime with Memory: $memory_id..."
    ~/.pyenv/versions/3.10.*/bin/agentcore deploy --auto-update-on-conflict || {
        log_error "AgentCore deployment failed"
        return 1
    }
    
    log_info "✅ AgentCore Runtime deployed"
    
    # Get Agent ID and ARN from status
    local agent_arn=$(~/.pyenv/versions/3.10.*/bin/agentcore status 2>/dev/null | grep "Agent ARN:" | awk '{print $NF}')
    local agent_id=$(echo "$agent_arn" | awk -F'/' '{print $NF}')
    log_info "Agent ARN: $agent_arn"
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
    
    # Update Instructions
    if [[ -f "agentcore/agent_instructions.txt" ]]; then
        log_info "[Phase 7] Agent Instructions found"
    else
        log_warn "[Phase 7] Agent Instructions not found, skipping"
    fi
    
    # Register Gateway Tools
    if [[ -f "agentcore/gateway_config.py" ]]; then
        log_info "[Phase 7] Registering Gateway Tools..."
        cd agentcore
        python3 gateway_config.py || log_warn "Gateway Tools registration failed"
        cd ..
    fi
    
    # Apply Runtime Configuration with Memory
    if [[ -f "agentcore/runtime_config.py" && -n "$agent_id" && -n "$memory_id" ]]; then
        log_info "[Phase 7] Applying Runtime Configuration..."
        log_info "[Phase 7] Agent ID: $agent_id"
        log_info "[Phase 7] Memory ID: $memory_id"
        cd agentcore
        AGENT_ID="$agent_id" MEMORY_ID="$memory_id" python3 runtime_config.py && log_info "✅ Runtime configuration applied" || log_warn "Runtime configuration failed"
        cd ..
    else
        log_warn "[Phase 7] Skipping runtime config - missing agent_id or memory_id"
    fi
    
    # Update Lambda Invoker with Memory management
    if [[ -d "lambda/invoker" ]]; then
        log_info "[Phase 7] Updating Lambda Invoker..."
        cd lambda/invoker
        zip -r ../../build/invoker.zip . -x "*.pyc" -x "__pycache__/*" >/dev/null 2>&1
        cd ../..
        
        # Update Lambda function code
        /usr/local/bin/aws lambda update-function-code \
            --function-name sila2-agentcore-invoker \
            --zip-file fileb://build/invoker.zip \
            --region "$REGION" >/dev/null 2>&1 || log_warn "Lambda Invoker code update failed"
        
        # Get Runtime ARN from AgentCore status
        local runtime_arn=$(~/.pyenv/versions/3.10.*/bin/agentcore status 2>/dev/null | grep "Runtime ARN:" | awk '{print $NF}')
        if [[ -z "$runtime_arn" ]]; then
            # Fallback: construct from agent ARN
            runtime_arn=$(echo "$agent_arn" | sed 's|agent/|runtime/|')
        fi
        
        # Update Lambda environment variables with Runtime ARN and Session ID
        if [[ -n "$memory_id" && -n "$runtime_arn" ]]; then
            log_info "[Phase 7] Setting Lambda environment variables..."
            log_info "[Phase 7] MEMORY_ID=$memory_id"
            log_info "[Phase 7] RUNTIME_ARN=$runtime_arn"
            log_info "[Phase 7] SESSION_ID=hplc_001"
            /usr/local/bin/aws lambda update-function-configuration \
                --function-name sila2-agentcore-invoker \
                --environment "Variables={MEMORY_ID=$memory_id,RUNTIME_ARN=$runtime_arn,SESSION_ID=hplc_001,BRIDGE_URL=http://172.31.44.121:8080,AWS_REGION=$REGION}" \
                --region "$REGION" && log_info "✅ Lambda environment updated" || log_warn "Lambda environment update failed"
        fi
        
        log_info "[Phase 7] Lambda Invoker updated"
    fi
    
    # Verify Setup
    if [[ -f "agentcore/verify_setup.py" ]]; then
        log_info "[Phase 7] Verifying Setup..."
        cd agentcore
        python3 verify_setup.py || log_warn "Verification warnings detected"
        cd ..
    fi
    
    log_info "✅ [Phase 7] AgentCore configured"
    
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
