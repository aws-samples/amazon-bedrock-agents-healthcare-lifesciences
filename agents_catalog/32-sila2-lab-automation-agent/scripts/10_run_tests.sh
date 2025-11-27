#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Phase 3 Integration Tests ==="
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    # 統合テスト実行
    log_info "Running Phase 3 integration tests..."
    python3 test_phase3_integration.py
    
    # アーキテクチャ検証
    log_info "Running architecture compliance verification..."
    bash verify_architecture_compliance.sh
    
    # パフォーマンステスト
    log_info "Running performance tests..."
    python3 performance_test.py
    
    log_info "All tests completed successfully"
}

main "$@"