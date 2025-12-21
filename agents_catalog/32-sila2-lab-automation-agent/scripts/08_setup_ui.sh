#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Streamlit UI Setup ==="
    
    cd "$(dirname "$SCRIPT_DIR")"
    
    echo "Select UI version:"
    echo "1) Phase 3 (AgentCore)"
    echo "2) Phase 5 (Polling & Properties)"
    echo "3) MCP Tools Test (All 5 tools)"
    read -p "Enter choice [1-3]: " choice
    
    case $choice in
        1)
            UI_FILE="streamlit_app_agentcore.py"
            log_info "Selected: Phase 3 UI"
            ;;
        2)
            UI_FILE="streamlit_app_phase5.py"
            log_info "Selected: Phase 5 UI"
            ;;
        3)
            UI_FILE="streamlit_mcp_tools.py"
            log_info "Selected: MCP Tools Test UI"
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
    
    pip install streamlit boto3 requests >/dev/null 2>&1
    
    cat > run_streamlit.sh << EOF
#!/bin/bash
export STREAMLIT_SERVER_PORT=8501
streamlit run $UI_FILE
EOF
    
    chmod +x run_streamlit.sh
    
    log_info "Streamlit UI setup complete"
    log_info "Run './run_streamlit.sh' to start the UI"
}

main "$@"