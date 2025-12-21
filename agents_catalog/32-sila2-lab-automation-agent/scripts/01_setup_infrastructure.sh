#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Step 01: Infrastructure Setup ==="
    
    if ! cd "$(dirname "$SCRIPT_DIR")"; then
        log_error "Failed to change to project directory"
        exit 1
    fi
    
    log_info "Creating ECR repositories..."
    aws ecr describe-repositories --repository-names sila2-bridge --region "$AWS_REGION" 2>/dev/null || \
      aws ecr create-repository --repository-name sila2-bridge --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true
    
    aws ecr describe-repositories --repository-names sila2-mock-devices --region "$AWS_REGION" 2>/dev/null || \
      aws ecr create-repository --repository-name sila2-mock-devices --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true
    
    log_info "✅ Step 01 complete - ECR repositories created"
    log_info "Next: ./scripts/02_build_containers.sh"
}

main "$@"
