# 🚀 Enrollment Pulse - Backend Deployment

This directory contains the complete backend system including source code, data, and AWS deployment files.

## 📁 Directory Structure

```
backend/
├── src/                        # Backend source code
│   ├── agent/                 # Strands Agent integration
│   ├── analysis/              # Clinical analytics
│   └── data/                  # Data processing
├── data/                      # CTMS demo data
├── backend_api.py             # Main FastAPI application
├── enrollment_lambda.py       # Lambda handler
├── template.yaml              # SAM CloudFormation template
├── build.sh                   # Build script
├── deploy_only.sh             # Deploy script
├── cleanup.sh                 # Cleanup script
├── requirements.txt           # Python dependencies
└── README.md                  # This guide
```

## ⚡ Quick Deploy

1. **Build**: `./build.sh`
2. **Deploy**: `./deploy_only.sh`
3. **Access**: Use the Lambda Function URL provided

## 📋 Prerequisites

### Required Tools
- AWS CLI installed and configured
- SAM CLI installed (`pip install aws-sam-cli`)
- Python 3.12+ with virtual environment
- AWS account with appropriate permissions

### Required Permissions
Your AWS user/role needs:
- CloudFormation, Lambda permissions
- IAM role creation and attachment permissions
- Bedrock model access (Claude 3.7 Sonnet)

### Bedrock Setup
- Request access to Claude models in AWS Bedrock console
- Ensure access in us-west-2 region

## 🚀 Step-by-Step Deployment

### 1. Prerequisites
- AWS CLI configured with credentials
- SAM CLI installed
- Docker installed (for container builds)

### 2. Deploy Backend
```bash
cd backend

# Build the Lambda package
./build.sh

# Deploy to AWS
./deploy_only.sh
```

### 3. Expected Output
```
🚀 Starting Enrollment Pulse AWS Deployment
============================================
📋 Deployment Configuration:
  Stage: dev
  Region: us-west-2
  Stack: enrollment-pulse-dev

🔍 Checking prerequisites...
✅ Prerequisites check passed

🔨 Building SAM application...
✅ SAM build completed

🚀 Deploying backend infrastructure...
✅ Backend deployed successfully

🎉 Deployment completed successfully!
============================================
📊 Access your application:
  🔗 Lambda Function URL: https://abc123.lambda-url.us-west-2.on.aws/
  📚 API Docs: https://abc123.lambda-url.us-west-2.on.aws/docs
```

### 4. Validate Deployment
```bash
curl https://your-lambda-function-url.lambda-url.us-west-2.on.aws/
```

## 🏗️ AWS Architecture

```
Lambda Function URL → Lambda (FastAPI) → Bedrock (Claude 3.7)
```

### Resources Created
- **Lambda Function**: `enrollment-pulse-api-dev`
- **Lambda Function URL**: Direct HTTPS endpoint
- **IAM Roles**: Lambda execution with Bedrock permissions

## 💰 Cost Estimation

### Lambda Function URL Deployment
- **Lambda**: ~$10-30/month (10GB memory, high usage)
- **Bedrock**: ~$20-100/month (Strands Agent usage)
- **Total**: ~$30-130/month

## ✨ Features

- **Strands Agent**: AI-powered clinical trial analysis
- **15-minute timeout**: Lambda Function URL support
- **IAM Security**: Secure access with AWS credentials
- **Real-time data**: CTMS data processing
- **Site-specific analysis**: Detailed per-site recommendations

## 🔧 Management Commands

```bash
# Build backend
./build.sh

# Deploy backend
./deploy_only.sh

# Clean up resources
./cleanup.sh

# View logs
aws logs tail /aws/lambda/enrollment-pulse-api-dev --follow

# Test deployment
curl https://your-lambda-function-url.lambda-url.us-west-2.on.aws/
```

## 🔄 Updates and Maintenance

### Deploy Updates
```bash
# Make code changes, then redeploy
./deploy_only.sh
```

### Monitor System
- **CloudWatch Logs**: Monitor Lambda function logs
- **CloudWatch Metrics**: Track Lambda performance
- **Cost Explorer**: Monitor AWS spending

### Scale for Production
1. Update template.yaml for production settings
2. Configure custom domain name (optional)
3. Set up monitoring and alerting
4. Implement API authentication if needed
5. Consider increasing Lambda memory/timeout

## 🐛 Troubleshooting

### Common Issues

1. **Bedrock Access Denied**
   - Request Claude model access in Bedrock console
   - Verify IAM permissions for Bedrock

2. **SAM Build Fails**
   - Use: `sam build --use-container`
   - Check Python dependencies

3. **Lambda Timeout**
   - Increase timeout in template.yaml
   - Monitor CloudWatch logs

4. **Function URL Issues**
   - Check Lambda Function URL configuration
   - Verify CORS settings in FastAPI

### Debug Commands
```bash
# Validate SAM template
sam validate

# Test locally
sam local start-api

# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name enrollment-pulse-dev
```

## 🧹 Cleanup

### Delete All Resources
```bash
./cleanup.sh
```

The cleanup script will:
- Prompt for confirmation before deletion
- Delete the CloudFormation stack
- Wait for complete resource cleanup
- Confirm successful deletion

**⚠️ Warning**: This will permanently delete all AWS resources and data.
