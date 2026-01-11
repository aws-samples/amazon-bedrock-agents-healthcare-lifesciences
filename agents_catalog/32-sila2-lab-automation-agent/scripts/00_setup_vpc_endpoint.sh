#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Step 00: VPC Endpoint Setup for Bedrock Agent Runtime ==="
    
    REGION=${AWS_REGION:-us-west-2}
    PHASE6_STACK="sila2-events-stack"
    ECS_STACK="sila2-bridge-ecs"
    
    # Try to get VPC info from Phase 6 CloudFormation stack
    log_info "Checking for existing CloudFormation stacks..."
    VPC_ID=$(/usr/local/bin/aws cloudformation describe-stacks \
        --stack-name $PHASE6_STACK \
        --query 'Stacks[0].Parameters[?ParameterKey==`VpcId`].ParameterValue' \
        --output text \
        --region $REGION 2>/dev/null || echo "")
    
    if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
        # Try ECS stack
        VPC_ID=$(/usr/local/bin/aws cloudformation describe-stacks \
            --stack-name $ECS_STACK \
            --query 'Stacks[0].Parameters[?ParameterKey==`VpcId`].ParameterValue' \
            --output text \
            --region $REGION 2>/dev/null || echo "")
    fi
    
    if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
        # Use default VPC
        log_info "No CloudFormation stack found, using default VPC..."
        VPC_ID=$(/usr/local/bin/aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" \
            --query 'Vpcs[0].VpcId' --output text --region $REGION)
    fi
    
    if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
        log_error "No VPC found. Please deploy infrastructure first."
        exit 1
    fi
    
    log_info "VPC ID: $VPC_ID"
    
    # Get subnets from Phase 6 stack or ECS stack
    SUBNET_IDS=$(/usr/local/bin/aws cloudformation describe-stacks \
        --stack-name $PHASE6_STACK \
        --query 'Stacks[0].Parameters[?ParameterKey==`PrivateSubnetIds`].ParameterValue' \
        --output text \
        --region $REGION 2>/dev/null || echo "")
    
    if [ -z "$SUBNET_IDS" ] || [ "$SUBNET_IDS" == "None" ]; then
        SUBNET_IDS=$(/usr/local/bin/aws cloudformation describe-stacks \
            --stack-name $ECS_STACK \
            --query 'Stacks[0].Parameters[?ParameterKey==`SubnetIds`].ParameterValue' \
            --output text \
            --region $REGION 2>/dev/null || echo "")
    fi
    
    if [ -z "$SUBNET_IDS" ] || [ "$SUBNET_IDS" == "None" ]; then
        # Get first 2 subnets from VPC
        SUBNET_IDS=$(/usr/local/bin/aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" \
            --query 'Subnets[0:2].SubnetId' --output text --region $REGION | tr '\t' ',')
    fi
    
    log_info "Subnets: $SUBNET_IDS"
    
    # Get security group from Phase 6 stack or create default
    SG_IDS=$(/usr/local/bin/aws cloudformation describe-stacks \
        --stack-name $PHASE6_STACK \
        --query 'Stacks[0].Parameters[?ParameterKey==`BridgeSecurityGroupId`].ParameterValue' \
        --output text \
        --region $REGION 2>/dev/null || echo "")
    
    if [ -z "$SG_IDS" ] || [ "$SG_IDS" == "None" ]; then
        SG_IDS=$(/usr/local/bin/aws cloudformation describe-stacks \
            --stack-name $ECS_STACK \
            --query 'Stacks[0].Outputs[?OutputKey==`BridgeSecurityGroup`].OutputValue' \
            --output text \
            --region $REGION 2>/dev/null || echo "")
    fi
    
    if [ -z "$SG_IDS" ] || [ "$SG_IDS" == "None" ]; then
        # Get default security group
        SG_IDS=$(/usr/local/bin/aws ec2 describe-security-groups \
            --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=default" \
            --query 'SecurityGroups[0].GroupId' --output text --region $REGION)
    fi
    
    log_info "Security Groups: $SG_IDS"
    
    # Check if VPC endpoint already exists
    SERVICE_NAME="com.amazonaws.${REGION}.bedrock-agentcore"
    log_info "Checking for existing VPC endpoint..."
    log_info "Service: $SERVICE_NAME"
    
    EXISTING_ENDPOINT=$(/usr/local/bin/aws ec2 describe-vpc-endpoints \
        --filters "Name=vpc-id,Values=$VPC_ID" "Name=service-name,Values=$SERVICE_NAME" \
        --query 'VpcEndpoints[0].VpcEndpointId' \
        --output text \
        --region $REGION)
    
    if [ "$EXISTING_ENDPOINT" != "None" ] && [ -n "$EXISTING_ENDPOINT" ]; then
        log_info "✅ VPC Endpoint already exists: $EXISTING_ENDPOINT"
        log_info "State: $(/usr/local/bin/aws ec2 describe-vpc-endpoints --vpc-endpoint-ids "$EXISTING_ENDPOINT" --query 'VpcEndpoints[0].State' --output text --region $REGION)"
        exit 0
    fi
    
    # Create VPC endpoint
    log_info "Creating VPC endpoint for Bedrock Agent Runtime..."
    
    IFS=',' read -ra SUBNET_ARRAY <<< "$SUBNET_IDS"
    IFS=',' read -ra SG_ARRAY <<< "$SG_IDS"
    
    SUBNET_PARAMS=""
    for subnet in "${SUBNET_ARRAY[@]}"; do
        SUBNET_PARAMS="$SUBNET_PARAMS $subnet"
    done
    
    SG_PARAMS=""
    for sg in "${SG_ARRAY[@]}"; do
        SG_PARAMS="$SG_PARAMS $sg"
    done
    
    ENDPOINT_ID=$(/usr/local/bin/aws ec2 create-vpc-endpoint \
        --vpc-id "$VPC_ID" \
        --vpc-endpoint-type Interface \
        --service-name "$SERVICE_NAME" \
        --subnet-ids $SUBNET_PARAMS \
        --security-group-ids $SG_PARAMS \
        --private-dns-enabled \
        --query 'VpcEndpoint.VpcEndpointId' \
        --output text \
        --region $REGION)
    
    log_info "✅ VPC Endpoint created: $ENDPOINT_ID"
    
    # Wait for endpoint to be available (manual polling)
    log_info "Waiting for VPC endpoint to become available..."
    for i in {1..30}; do
        STATE=$(/usr/local/bin/aws ec2 describe-vpc-endpoints \
            --vpc-endpoint-ids "$ENDPOINT_ID" \
            --query 'VpcEndpoints[0].State' \
            --output text \
            --region $REGION)
        
        if [ "$STATE" == "available" ]; then
            log_info "✅ VPC Endpoint is now available"
    
    # Add inbound HTTPS rule to VPC endpoint security groups
    log_info "Configuring VPC endpoint security group inbound rules..."
    for sg in "${SG_ARRAY[@]}"; do
        INBOUND_HTTPS=$(/usr/local/bin/aws ec2 describe-security-groups \
            --group-ids "$sg" \
            --query "SecurityGroups[0].IpPermissions[?IpProtocol=='tcp' && FromPort==\`443\` && ToPort==\`443\`]" \
            --output json \
            --region $REGION)
        
        if [ "$INBOUND_HTTPS" == "[]" ]; then
            log_info "Adding inbound HTTPS rule to VPC endpoint SG $sg..."
            /usr/local/bin/aws ec2 authorize-security-group-ingress \
                --group-id "$sg" \
                --protocol tcp \
                --port 443 \
                --cidr 0.0.0.0/0 \
                --region $REGION || true
        else
            log_info "✅ VPC endpoint SG $sg already has inbound HTTPS rule"
        fi
    done
            break
        fi
        
        log_info "Current state: $STATE (attempt $i/30)"
        sleep 10
    done
    
    # Verify security group allows outbound HTTPS
    log_info "Verifying security group configuration..."
    for sg in "${SG_ARRAY[@]}"; do
        HTTPS_RULE=$(/usr/local/bin/aws ec2 describe-security-groups \
            --group-ids "$sg" \
            --query "SecurityGroups[0].IpPermissionsEgress[?IpProtocol=='tcp' && FromPort==\`443\` && ToPort==\`443\`]" \
            --output json \
            --region $REGION)
        
        if [ "$HTTPS_RULE" == "[]" ]; then
            log_warn "Security Group $sg does not have outbound HTTPS rule"
            log_info "Adding outbound HTTPS rule..."
            /usr/local/bin/aws ec2 authorize-security-group-egress \
                --group-id "$sg" \
                --protocol tcp \
                --port 443 \
                --cidr 0.0.0.0/0 \
                --region $REGION || true
        else
            log_info "✅ Security Group $sg has outbound HTTPS rule"
        fi
    done
    
    log_info ""
    log_info "=== VPC Endpoint Setup Complete ==="
    log_info "Endpoint ID: $ENDPOINT_ID"
    log_info "Service: $SERVICE_NAME"
    log_info "Private DNS: Enabled"
    log_info ""
    log_info "Lambda can now access Bedrock Agent Runtime API via VPC endpoint"
    log_info ""
    log_info "Next: Test Lambda function"
    log_info "  /usr/local/bin/aws lambda invoke --function-name sila2-agentcore-invoker \\"
    log_info "    --cli-binary-format raw-in-base64-out \\"
    log_info "    --payload '{\"action\":\"periodic\",\"devices\":[\"hplc\"]}' \\"
    log_info "    --region $REGION /tmp/response.json"
}

main "$@"
