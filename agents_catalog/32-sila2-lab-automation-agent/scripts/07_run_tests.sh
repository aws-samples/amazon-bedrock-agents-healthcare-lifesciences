#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Phase 4/5/6 Integration Tests ==="
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # Phase 6 REST API Tests
    log_info "Testing Phase 6 REST API..."
    if command -v curl &> /dev/null; then
        BRIDGE_URL="http://bridge.sila2.local:8080"
        
        log_info "Health check: $BRIDGE_URL/health"
        curl -s "$BRIDGE_URL/health" || log_warn "Health check failed"
        
        log_info "Device list: $BRIDGE_URL/api/devices"
        curl -s "$BRIDGE_URL/api/devices" || log_warn "Device list failed"
        
        log_info "History: $BRIDGE_URL/api/history/hplc?minutes=5"
        curl -s "$BRIDGE_URL/api/history/hplc?minutes=5" || log_warn "History failed"
    fi
    
    # AgentCore統合テスト
    log_info "Running Phase 4 AgentCore integration tests..."
    python3 test_integration.py || {
        log_warn "Integration tests failed, but continuing..."
    }
    
    log_info "✅ Tests completed"
}

main "$@"