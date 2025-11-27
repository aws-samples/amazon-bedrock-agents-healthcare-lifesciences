#!/bin/bash

VALIDATION_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$VALIDATION_SCRIPT_DIR/common.sh"

validate_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found"
        exit 1
    fi
    
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured"
        exit 1
    fi
    
    log_info "AWS CLI validated"
}

validate_agentcore_cli() {
    # .pyenv環境のagentcoreをチェック
    local agentcore_path="$HOME/.pyenv/shims/agentcore"
    if [[ -f "$agentcore_path" ]]; then
        export PATH="$HOME/.pyenv/shims:$PATH"
        log_info "AgentCore CLI validated (using .pyenv)"
        return 0
    elif command -v agentcore &> /dev/null; then
        log_info "AgentCore CLI validated (using PATH)"
        return 0
    else
        log_warn "AgentCore CLI not found in .pyenv or PATH"
        return 1
    fi
}

validate_project_files() {
    local project_root="/home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent"
    local required_files=(
        "$project_root/main_strands_agentcore_phase3.py"
        "$project_root/requirements.txt"
        "$project_root/gateway/agentcore_gateway_tools.py"
        "$project_root/gateway/mcp_tool_registry.py"
        "$project_root/infrastructure/device_api_gateway_enhanced.yaml"
    )
    
    local missing_files=()
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$(basename "$file")")
        fi
    done
    
    # Check optional AgentCore config
    if [[ ! -f "$project_root/.bedrock_agentcore.yaml" ]]; then
        log_warn "AgentCore config not found, will be created during deployment"
    fi
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        log_error "Missing required files: ${missing_files[*]}"
        exit 1
    fi
    
    log_info "Project files validated"
}

validate_environment() {
    log_info "Validating deployment environment..."
    
    validate_aws_cli
    
    # AgentCore CLIは警告のみ、デプロイは続行
    if ! validate_agentcore_cli; then
        log_warn "AgentCore CLI not found - some features may be limited"
    fi
    
    validate_project_files
    
    log_info "Environment validation complete"
}