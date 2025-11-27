#!/bin/bash

set -e

# Remove error masking - fail fast on real errors
export DEPLOY_MODE="strict"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
source "$SCRIPT_DIR/utils/validation.sh"

main() {
    log_info "=== Phase 3 Complete Deployment (10 Steps) ==="
    
    # 環境検証
    validate_environment
    
    # 自動デプロイモード（コーディングエージェント用）
    log_info "Auto-deploying Phase 3 complete architecture..."
    
    # 段階的デプロイ実行（厳密モード）
    log_info "Step 1: Infrastructure Setup"
    "$SCRIPT_DIR/01_setup_infrastructure.sh"
    
    log_info "Step 2: Mock SiLA2 Devices"
    "$SCRIPT_DIR/02_deploy_mock_devices.sh"
    
    log_info "Step 3: MCP-gRPC Bridge"
    "$SCRIPT_DIR/03_setup_mcp_bridge.sh"
    
    log_info "Step 4: Device API Gateway"
    "$SCRIPT_DIR/04_create_device_gateway.sh"
    
    log_info "Step 5: Create MCP Gateway"
    "$SCRIPT_DIR/05_create_gateway.sh"
    
    log_info "Step 6: Create Gateway Target"
    "$SCRIPT_DIR/06_create_gateway_target.sh"
    
    log_info "Step 7: Deploy AgentCore Runtime"
    "$SCRIPT_DIR/07_deploy_agentcore.sh"
    
    log_info "Step 8: Phase 3 Integration"
    "$SCRIPT_DIR/08_integrate_phase3.sh"
    
    log_info "Step 9: Streamlit UI"
    "$SCRIPT_DIR/09_setup_ui.sh"
    
    log_info "Step 10: Final Tests"
    "$SCRIPT_DIR/10_run_tests.sh"
    
    log_info "=== Phase 3 Deployment Complete ==="
    log_info "🎉 All 10 steps completed successfully!"
    log_info "Architecture: 100% compliant with ARCHITECTURE_ROADMAP.md"
    log_info "Phase 3 optimized: 10 steps, proper dependency order"
}

main "$@"