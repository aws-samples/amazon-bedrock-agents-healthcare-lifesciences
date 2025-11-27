#!/bin/bash

export PROJECT_NAME="sila2-lab-automation"
export AWS_REGION="${AWS_REGION:-us-west-2}"
export STACK_PREFIX="sila2-phase3"

log_info() { echo -e "\033[32m[INFO]\033[0m $1"; }
log_warn() { echo -e "\033[33m[WARN]\033[0m $1"; }
log_error() { echo -e "\033[31m[ERROR]\033[0m $1"; }

confirm_action() {
    read -p "$1 (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

check_stack_exists() {
    aws cloudformation describe-stacks --stack-name "$1" --region "$AWS_REGION" >/dev/null 2>&1
}

check_file_exists() {
    if [[ ! -f "$1" ]]; then
        log_warn "File not found: $1 (skipping)"
        return 1
    fi
    return 0
}

wait_for_stack() {
    local stack_name="$1"
    local operation="$2"
    
    log_info "Waiting for stack $operation to complete..."
    aws cloudformation wait "stack-${operation}-complete" \
        --stack-name "$stack_name" \
        --region "$AWS_REGION"
}