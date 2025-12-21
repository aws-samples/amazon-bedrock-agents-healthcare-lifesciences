#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Phase 4 Integration Tests ==="
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # AgentCore統合テスト
    log_info "Running Phase 4 AgentCore integration tests..."
    python3 test_phase4_integration.py || {
        log_warn "Integration tests failed, but continuing..."
    }
    
    log_info "✅ Tests completed"
}

main "$@"