#!/bin/bash

set -e
set -o pipefail

# ----- Config -----
PROJECT_NAME=${1:-genomics-vep-pipeline}
INFRA_STACK_NAME=${2:-${PROJECT_NAME}-infrastructure}
REGION=$(aws configure get region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# AgentCore specific resources
AGENT_NAME=${3:-genomicsapp_vcf_agent_supervisor}
MEMORY_NAME=${4:-genomicsapp}
SSM_PARAM="/app/researchapp/agentcore/memory_id"

# S3 Buckets (from CloudFormation)
VCF_INPUT_BUCKET="genomics-vcf-input-bucket-${ACCOUNT_ID}-${REGION}"
VEP_OUTPUT_BUCKET="genomics-vep-output-bucket-${ACCOUNT_ID}-${REGION}"

echo "🧹 Genomics Agent Cleanup Script"
echo "================================"
echo "Project: $PROJECT_NAME"
echo "Stack: $INFRA_STACK_NAME"
echo "Agent: $AGENT_NAME"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""

# ----- Confirm Deletion -----
read -p "⚠️ Are you sure you want to delete ALL genomics agent resources? This includes:
- CloudFormation stack: $INFRA_STACK_NAME
- AgentCore agent: $AGENT_NAME
- AgentCore memory: $MEMORY_NAME
- S3 buckets and contents
- HealthOmics stores (variant/annotation)
- DynamoDB tables
- Lambda functions
- IAM roles
(y/N): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "❌ Cleanup cancelled."
  exit 1
fi

echo ""
echo "🚀 Starting cleanup process..."

# ----- 1. Delete AgentCore Resources -----
echo ""
echo "🤖 Cleaning up AgentCore resources..."

# Delete AgentCore agent
echo "🗑️ Deleting AgentCore agent: $AGENT_NAME"
if command -v agentcore &> /dev/null; then
    agentcore delete --name "$AGENT_NAME" --force || echo "⚠️ Agent may not exist or already deleted"
else
    echo "⚠️ agentcore CLI not found, skipping agent deletion"
fi

# Delete AgentCore memory
echo "🧠 Deleting AgentCore memory: $MEMORY_NAME"
if [ -f "scripts/agentcore_memory.py" ]; then
    python scripts/agentcore_memory.py delete --confirm || echo "⚠️ Memory may not exist or already deleted"
else
    echo "⚠️ agentcore_memory.py not found, skipping memory deletion"
fi

# ----- 2. Delete HealthOmics Resources -----
echo ""
echo "🧬 Cleaning up HealthOmics resources..."

# List and delete variant stores
echo "🔬 Deleting variant stores..."
aws omics list-variant-stores --region "$REGION" --query 'variantStores[?contains(name, `genomicsvariantstore`)].id' --output text | while read -r store_id; do
    if [ -n "$store_id" ]; then
        echo "  Deleting variant store: $store_id"
        aws omics delete-variant-store --name "$store_id" --region "$REGION" || echo "  ⚠️ Failed to delete variant store $store_id"
    fi
done

# List and delete annotation stores
echo "🏷️ Deleting annotation stores..."
aws omics list-annotation-stores --region "$REGION" --query 'annotationStores[?contains(name, `genomicsannotationstore`)].id' --output text | while read -r store_id; do
    if [ -n "$store_id" ]; then
        echo "  Deleting annotation store: $store_id"
        aws omics delete-annotation-store --name "$store_id" --region "$REGION" || echo "  ⚠️ Failed to delete annotation store $store_id"
    fi
done

# List and delete reference stores
echo "🧬 Deleting reference stores..."
aws omics list-reference-stores --region "$REGION" --query 'referenceStores[?contains(name, `genomics-reference-store`)].id' --output text | while read -r store_id; do
    if [ -n "$store_id" ]; then
        echo "  Deleting reference store: $store_id"
        aws omics delete-reference-store --id "$store_id" --region "$REGION" || echo "  ⚠️ Failed to delete reference store $store_id"
    fi
done

# ----- 3. Clean S3 Buckets -----
echo ""
echo "🪣 Cleaning up S3 buckets..."

# Clean VCF input bucket
if aws s3 ls "s3://$VCF_INPUT_BUCKET" &>/dev/null; then
    echo "🧹 Emptying VCF input bucket: $VCF_INPUT_BUCKET"
    aws s3 rm "s3://$VCF_INPUT_BUCKET" --recursive || echo "⚠️ Failed to clean VCF input bucket"
else
    echo "ℹ️ VCF input bucket does not exist: $VCF_INPUT_BUCKET"
fi

# Clean VEP output bucket
if aws s3 ls "s3://$VEP_OUTPUT_BUCKET" &>/dev/null; then
    echo "🧹 Emptying VEP output bucket: $VEP_OUTPUT_BUCKET"
    aws s3 rm "s3://$VEP_OUTPUT_BUCKET" --recursive || echo "⚠️ Failed to clean VEP output bucket"
else
    echo "ℹ️ VEP output bucket does not exist: $VEP_OUTPUT_BUCKET"
fi

# ----- 4. Delete CloudFormation Stack -----
echo ""
echo "☁️ Deleting CloudFormation stack..."

if aws cloudformation describe-stacks --stack-name "$INFRA_STACK_NAME" --region "$REGION" &>/dev/null; then
    echo "🧨 Deleting stack: $INFRA_STACK_NAME"
    aws cloudformation delete-stack --stack-name "$INFRA_STACK_NAME" --region "$REGION"
    
    echo "⏳ Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name "$INFRA_STACK_NAME" --region "$REGION"
    echo "✅ Stack $INFRA_STACK_NAME deleted successfully"
else
    echo "ℹ️ Stack does not exist: $INFRA_STACK_NAME"
fi

# ----- 5. Clean up ECR repositories -----
echo ""
echo "🐳 Cleaning up ECR repositories..."

# Delete VEP ECR repository if it exists
VEP_REPO_NAME="genomics-vep"
if aws ecr describe-repositories --repository-names "$VEP_REPO_NAME" --region "$REGION" &>/dev/null; then
    echo "🗑️ Deleting ECR repository: $VEP_REPO_NAME"
    aws ecr delete-repository --repository-name "$VEP_REPO_NAME" --force --region "$REGION" || echo "⚠️ Failed to delete ECR repository"
else
    echo "ℹ️ ECR repository does not exist: $VEP_REPO_NAME"
fi

# ----- 6. Clean up SSM parameters -----
echo ""
echo "🔧 Cleaning up SSM parameters..."

# Delete AgentCore memory SSM parameter
if aws ssm get-parameter --name "$SSM_PARAM" --region "$REGION" &>/dev/null; then
    echo "🗑️ Deleting SSM parameter: $SSM_PARAM"
    aws ssm delete-parameter --name "$SSM_PARAM" --region "$REGION" || echo "⚠️ Failed to delete SSM parameter"
else
    echo "ℹ️ SSM parameter does not exist: $SSM_PARAM"
fi

# ----- 7. Clean up local files -----
echo ""
echo "🗂️ Cleaning up local files..."

# Remove Docker-related files
echo "🐳 Removing Docker files..."
rm -f Dockerfile docker-compose.yml || echo "ℹ️ No Docker files to remove"

# Remove AgentCore generated files
echo "🤖 Removing AgentCore files..."
rm -f .agentcore_config.json || echo "ℹ️ No AgentCore config to remove"

# Remove Python cache
echo "🐍 Removing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "✅ Cleanup completed successfully!"
echo ""
echo "📋 Summary of cleaned resources:"
echo "  ✓ AgentCore agent: $AGENT_NAME"
echo "  ✓ AgentCore memory: $MEMORY_NAME"
echo "  ✓ CloudFormation stack: $INFRA_STACK_NAME"
echo "  ✓ S3 buckets: $VCF_INPUT_BUCKET, $VEP_OUTPUT_BUCKET"
echo "  ✓ HealthOmics stores (variant, annotation, reference)"
echo "  ✓ ECR repositories"
echo "  ✓ SSM parameters"
echo "  ✓ Local cache files"
echo ""
echo "🎉 All genomics agent resources have been cleaned up!"
