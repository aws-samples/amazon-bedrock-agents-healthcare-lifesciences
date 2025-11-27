#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Phase 3 Streamlit UI Setup ==="
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    pip install streamlit boto3 requests >/dev/null 2>&1
    
    cat > run_streamlit.sh << 'EOF'
#!/bin/bash
export STREAMLIT_SERVER_PORT=8501
streamlit run streamlit_app_agentcore.py
EOF
    
    chmod +x run_streamlit.sh
    
    log_info "Streamlit UI setup complete"
    log_info "Run './run_streamlit.sh' to start the UI"
}

main "$@"