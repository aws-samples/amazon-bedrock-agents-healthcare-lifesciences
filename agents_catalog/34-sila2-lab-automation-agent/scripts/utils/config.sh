#!/bin/bash
# Common configuration

# AWS configuration
export DEFAULT_REGION="${AWS_REGION:-us-west-2}"
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Stack name
export MAIN_STACK_NAME="sila2-main-stack"

# S3 bucket (for Lambda/CFn templates)
export DEPLOYMENT_BUCKET="sila2-deployment-${ACCOUNT_ID}-${DEFAULT_REGION}"

# ECR repositories
export ECR_BRIDGE="sila2-bridge"
export ECR_MOCK="sila2-mock-devices"

# Environment
export ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-dev}"
