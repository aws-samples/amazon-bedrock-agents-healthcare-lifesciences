#!/bin/bash

# Enrollment Pulse - AWS Cleanup Script
# Deletes all AWS resources created by the deployment

set -e

STACK_NAME="enrollment-pulse-dev"
REGION="us-west-2"

echo "🧹 Enrollment Pulse - AWS Cleanup"
echo "=================================="
echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Check if stack exists
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "⚠️  WARNING: This will permanently delete all AWS resources!"
    echo "   - Lambda Function: enrollment-pulse-api-dev"
    echo "   - Lambda Function URL"
    echo "   - IAM Roles and Policies"
    echo "   - CloudWatch Log Groups"
    echo ""
    
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deleting CloudFormation stack..."
        aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
        
        echo "⏳ Waiting for stack deletion to complete..."
        aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"
        
        echo "✅ Cleanup completed successfully!"
        echo "All AWS resources have been deleted."
    else
        echo "❌ Cleanup cancelled."
        exit 1
    fi
else
    echo "ℹ️  Stack '$STACK_NAME' not found. Nothing to clean up."
fi