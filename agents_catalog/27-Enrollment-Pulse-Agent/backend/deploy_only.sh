#!/bin/bash

echo "🚀 Deploying Enrollment Pulse Backend..."

# Store deployment info
DEPLOYMENT_INFO_FILE="deployment_info.txt"

# Clean up old deployment info
rm -f "$DEPLOYMENT_INFO_FILE"

# Check if AWS credentials are available
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ AWS credentials not found in environment variables"
    echo "Please set AWS credentials using one of these methods:"
    echo ""
    echo "Option 1: Environment variables"
    echo "export AWS_ACCESS_KEY_ID=your_key"
    echo "export AWS_SECRET_ACCESS_KEY=your_secret"
    echo "export AWS_DEFAULT_REGION=us-west-2"
    echo ""
    echo "Option 2: Load from ~/.aws/credentials"
    echo 'export AWS_ACCESS_KEY_ID=$(grep -A 2 "[default]" ~/.aws/credentials | grep "aws_access_key_id" | cut -d"=" -f2 | tr -d " ")'
    echo 'export AWS_SECRET_ACCESS_KEY=$(grep -A 2 "[default]" ~/.aws/credentials | grep "aws_secret_access_key" | cut -d"=" -f2 | tr -d " ")'
    echo "export AWS_DEFAULT_REGION=us-west-2"
    echo ""
    echo "Option 3: Use AWS CLI profile"
    echo "sam deploy --profile default ..."
    echo ""
    exit 1
else
    echo "✅ AWS credentials found in environment"
fi

# Fix upload timeout issues for large packages
export AWS_CLI_READ_TIMEOUT=0
export AWS_CLI_FILE_TIMEOUT=0

# Set default region if not set
if [ -z "$AWS_DEFAULT_REGION" ]; then
    export AWS_DEFAULT_REGION=us-west-2
fi

echo "🌍 Using AWS region: $AWS_DEFAULT_REGION"

# Deploy to AWS
sam deploy --stack-name enrollment-pulse-backend \
           --capabilities CAPABILITY_IAM \
           --region "$AWS_DEFAULT_REGION" \
           --resolve-s3 \
           --no-confirm-changeset

if [ $? -eq 0 ]; then
    echo "✅ Deployment complete!"
    echo ""
    echo "📋 Deployment URLs:"
    
    # Get API Gateway URL from CloudFormation outputs
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name enrollment-pulse-backend \
        --region "$AWS_DEFAULT_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
        --output text 2>/dev/null)
    
    # Get Lambda Function URL
    FUNCTION_URL=$(aws lambda get-function-url-config \
        --function-name enrollment-pulse-backend \
        --region "$AWS_DEFAULT_REGION" \
        --query 'FunctionUrl' \
        --output text 2>/dev/null)
    
    if [ ! -z "$API_URL" ] && [ "$API_URL" != "None" ]; then
        echo "🌐 API Gateway URL: $API_URL"
    fi
    
    if [ ! -z "$FUNCTION_URL" ] && [ "$FUNCTION_URL" != "None" ]; then
        echo "⚡ Lambda Function URL: $FUNCTION_URL"
        echo ""
        echo "💡 Use the Lambda Function URL for direct access (requires IAM authentication)"
    fi
    
    # Save deployment info to file
    echo "# Enrollment Pulse Backend Deployment Info" > "$DEPLOYMENT_INFO_FILE"
    echo "# Generated on: $(date)" >> "$DEPLOYMENT_INFO_FILE"
    echo "" >> "$DEPLOYMENT_INFO_FILE"
    
    if [ ! -z "$API_URL" ] && [ "$API_URL" != "None" ]; then
        echo "API_GATEWAY_URL=$API_URL" >> "$DEPLOYMENT_INFO_FILE"
    fi
    
    if [ ! -z "$FUNCTION_URL" ] && [ "$FUNCTION_URL" != "None" ]; then
        # Remove trailing slash if present
        CLEAN_FUNCTION_URL=$(echo "$FUNCTION_URL" | sed 's/\/$//g')
        echo "LAMBDA_FUNCTION_URL=$CLEAN_FUNCTION_URL" >> "$DEPLOYMENT_INFO_FILE"
    fi
    
    echo "" >> "$DEPLOYMENT_INFO_FILE"
    echo "# Usage:" >> "$DEPLOYMENT_INFO_FILE"
    echo "# source $DEPLOYMENT_INFO_FILE" >> "$DEPLOYMENT_INFO_FILE"
    echo "# echo \$LAMBDA_FUNCTION_URL" >> "$DEPLOYMENT_INFO_FILE"
    
    echo ""
    echo "💾 Deployment info saved to: $DEPLOYMENT_INFO_FILE"
else
    echo "❌ Deployment failed!"
    exit 1
fi