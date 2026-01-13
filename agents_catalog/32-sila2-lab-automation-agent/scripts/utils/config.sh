#!/bin/bash
# 共通設定

# AWS設定
export DEFAULT_REGION="${AWS_REGION:-us-west-2}"
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# スタック名
export MAIN_STACK_NAME="sila2-main-stack"

# S3バケット（Lambda/CFnテンプレート用）
export DEPLOYMENT_BUCKET="sila2-deployment-${ACCOUNT_ID}-${DEFAULT_REGION}"

# ECRリポジトリ
export ECR_BRIDGE="sila2-bridge"
export ECR_MOCK="sila2-mock-devices"

# 環境
export ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-dev}"
