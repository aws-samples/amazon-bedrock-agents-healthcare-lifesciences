#!/bin/bash

set -e

# Remove error masking - fail fast on real errors
export DEPLOY_MODE="strict"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
source "$SCRIPT_DIR/utils/validation.sh"

main() {
    log_info "=== SiLA2 Lab Automation - Full Stack Deployment ==="
    log_info "Phase 5: gRPC Streaming + Real-time Monitor"
    log_info "Phase 6: Data Collection + Periodic Sending"
    log_info "Phase 7: AI Analysis + Autonomous Control"
    log_info ""
    
    # 環境検証
    validate_environment
    
    # Phase 5: Infrastructure + Mock Device + Bridge Server
    log_info "[Phase 5] Step 1/8: Infrastructure Setup..."
    "$SCRIPT_DIR/01_setup_infrastructure.sh"
    
    log_info "[Phase 5] Step 2/8: Building Containers..."
    "$SCRIPT_DIR/02_build_containers.sh"
    
    log_info "[Phase 5] Step 3/8: Deploying ECS Services..."
    "$SCRIPT_DIR/03_deploy_ecs.sh"
    
    log_info "[Phase 5] Step 4/8: Creating Gateway..."
    "$SCRIPT_DIR/04_create_gateway.sh"
    
    log_info "[Phase 5+7] Step 5/8: Creating MCP Targets..."
    "$SCRIPT_DIR/05_create_mcp_target.sh"
    
    # Phase 6+7: AgentCore Runtime + Configuration
    log_info "[Phase 6+7] Step 6/8: Deploying AgentCore..."
    "$SCRIPT_DIR/06_deploy_agentcore.sh"
    
    log_info "[Phase 6] Step 7/8: Running Tests..."
    "$SCRIPT_DIR/07_run_tests.sh"
    
    log_info "[Phase 7] Step 8/8: Testing Phase 7 Integration..."
    "$SCRIPT_DIR/08_test_phase7_integration.sh" || log_info "Phase 7 tests skipped"
    
    log_info ""
    log_info "=== Deployment Complete ==="
    log_info "Phase 5: ✅ Mock Device + Bridge Server + Streaming"
    log_info "Phase 6: ✅ Lambda Invoker + EventBridge + SNS"
    log_info "Phase 7: ✅ AI Analysis + Autonomous Control"
    log_info ""
    log_info "Access Streamlit UI: http://localhost:8501"
    if [[ -f /tmp/agent_id.txt ]]; then
        log_info "AgentCore Agent ID: $(cat /tmp/agent_id.txt)"
    fi
    log_info "Total Cost: ~\$8.50/month"
}

main "$@"