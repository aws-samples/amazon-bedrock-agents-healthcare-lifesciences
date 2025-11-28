#!/bin/bash

set -e

# Remove error masking - fail fast on real errors
export DEPLOY_MODE="strict"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
source "$SCRIPT_DIR/utils/validation.sh"

main() {
    log_info "=== Phase 4 Complete Deployment (9 Steps) ==="
    log_info "Lambda Proxy + MCP + gRPC Architecture"
    
    # 環境検証
    validate_environment
    
    # 自動デプロイモード
    log_info "Auto-deploying Phase 4 architecture..."
    
    # 段階的デプロイ実行
    log_info "Step 1: Infrastructure Setup"
    "$SCRIPT_DIR/01_setup_infrastructure.sh"
    
    log_info "Step 2: Build Containers (Bridge + Mock Device)"
    "$SCRIPT_DIR/02_build_containers.sh"
    
    log_info "Step 3: Deploy ECS + Lambda Proxy"
    "$SCRIPT_DIR/03_deploy_ecs.sh"
    
    log_info "Step 4: Create AgentCore Gateway"
    "$SCRIPT_DIR/04_create_gateway.sh"
    
    log_info "Step 5: Create Lambda MCP Target"
    "$SCRIPT_DIR/05_create_mcp_target.sh"
    
    log_info "Step 6: Deploy AgentCore Runtime"
    "$SCRIPT_DIR/06_deploy_agentcore.sh"
    
    log_info "Step 7: Run Integration Tests"
    "$SCRIPT_DIR/07_run_tests.sh"
    
    log_info "Step 8: Setup UI (Optional)"
    "$SCRIPT_DIR/08_setup_ui.sh" || log_info "UI setup skipped"
    
    log_info "Step 9: Cleanup NLB (Optional)"
    read -p "Delete old NLB resources? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "$SCRIPT_DIR/09_cleanup_nlb.sh"
    fi
    
    log_info "=== Phase 4 Deployment Complete ==="
    log_info "🎉 All steps completed successfully!"
    log_info "Architecture: Lambda Proxy + MCP + gRPC"
    log_info "Cost: ~\$16/month (70% reduction with NLB cleanup)"
}

main "$@"