#!/bin/bash

# ============================================================================
# Variant S3 Tables Interpreter Agent - Unified Deployment Script
# ============================================================================
# This script combines prerequisites setup and S3 Tables deployment
# Region: us-west-2
# Version: 3.0 (Unified)
# ============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_FILE="${SCRIPT_DIR}/deployment-config.env"

# Default values
export AWS_REGION="${AWS_REGION:-us-west-2}"
export STACK_NAME="${STACK_NAME:-genomics-vep-s3tables}"
export VEP_VERSION="release_113.4"
export REFERENCE_STORE_NAME="genomics-reference-store"

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "\n${PURPLE}════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  $1${NC}"
    echo -e "${PURPLE}════════════════════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Step $1: $2${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

# ============================================================================
# Prerequisites Check
# ============================================================================

check_prerequisites() {
    print_header "Checking Prerequisites"

    local missing=0

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found"
        missing=1
    else
        print_success "AWS CLI found"
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found"
        missing=1
    else
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python ${PYTHON_VERSION} found"
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found (optional for VEP container setup)"
    else
        print_success "Docker found"
    fi

    # Check curl
    if ! command -v curl &> /dev/null; then
        print_error "curl not found"
        missing=1
    else
        print_success "curl found"
    fi

    # Check jq (optional)
    if ! command -v jq &> /dev/null; then
        print_warning "jq not found (optional but recommended)"
    else
        print_success "jq found"
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null 2>&1; then
        print_error "AWS credentials not configured"
        missing=1
    else
        export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        print_success "AWS credentials configured"
        print_info "Account ID: ${AWS_ACCOUNT_ID}"
        print_info "Region: ${AWS_REGION}"
    fi

    if [ $missing -eq 1 ]; then
        print_error "Please install missing prerequisites and try again"
        exit 1
    fi

    # Set derived variables
    export VEP_CACHE_BUCKET="genomics-vep-cache-${AWS_ACCOUNT_ID}-${AWS_REGION}"
    export CLINVAR_BUCKET="genomics-clinvar-${AWS_ACCOUNT_ID}-${AWS_REGION}"
    export ECR_REPOSITORY_NAME="genomics-vep"
}

# Load configuration
load_config() {
    if [ -f "${CONFIG_FILE}" ]; then
        print_info "Loading configuration from ${CONFIG_FILE}"
        source "${CONFIG_FILE}"
        print_success "Configuration loaded"
    fi
}

# Save configuration
save_config() {
    print_info "Saving configuration to ${CONFIG_FILE}"
    cat > "${CONFIG_FILE}" << EOF
# Unified Deployment Configuration
# Generated on $(date)

# Basic Configuration
AWS_REGION=${AWS_REGION}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
STACK_NAME=${STACK_NAME}

# Prerequisites Resources
VEP_CACHE_BUCKET=${VEP_CACHE_BUCKET}
CLINVAR_BUCKET=${CLINVAR_BUCKET}
ECR_REPOSITORY_NAME=${ECR_REPOSITORY_NAME}
VEP_VERSION=${VEP_VERSION}
REFERENCE_STORE_NAME=${REFERENCE_STORE_NAME}
REFERENCE_STORE_ID=${REFERENCE_STORE_ID:-}

# S3 Tables Resources
VCF_INPUT_BUCKET=${VCF_INPUT_BUCKET:-}
VEP_OUTPUT_BUCKET=${VEP_OUTPUT_BUCKET:-}
DYNAMODB_TABLE=${DYNAMODB_TABLE:-}
LAMBDA_ROLE_ARN=${LAMBDA_ROLE_ARN:-}
OMICS_ROLE_ARN=${OMICS_ROLE_ARN:-}
TABLE_BUCKET_ARN=${TABLE_BUCKET_ARN:-}
WORKFLOW_ID=${WORKFLOW_ID:-}
EOF
    print_success "Configuration saved"
}

# ============================================================================
# PREREQUISITES SETUP STEPS (Steps 1-4)
# ============================================================================

# Step 1: VEP Cache Setup
setup_vep_cache() {
    print_step "1" "Setting up VEP Cache Files"

    # Create S3 bucket for VEP cache
    print_info "Creating S3 bucket: ${VEP_CACHE_BUCKET}"
    if aws s3 ls "s3://${VEP_CACHE_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://${VEP_CACHE_BUCKET}" --region ${AWS_REGION}

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${VEP_CACHE_BUCKET}" \
            --versioning-configuration Status=Enabled

        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "${VEP_CACHE_BUCKET}" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
        print_success "Bucket created: ${VEP_CACHE_BUCKET}"
    else
        print_warning "Bucket already exists: ${VEP_CACHE_BUCKET}"
    fi

    # Download VEP cache
    print_info "Downloading VEP cache files (this may take 10-15 minutes)..."
    if [ ! -f "homo_sapiens_vep_111_GRCh38.tar.gz" ]; then
        curl -O https://ftp.ensembl.org/pub/release-111/variation/indexed_vep_cache/homo_sapiens_vep_111_GRCh38.tar.gz
        print_success "VEP cache downloaded"
    else
        print_warning "VEP cache already downloaded"
    fi

    # Extract cache
    print_info "Extracting VEP cache..."
    if [ ! -d "homo_sapiens" ]; then
        tar xzf homo_sapiens_vep_111_GRCh38.tar.gz
        print_success "VEP cache extracted"
    else
        print_warning "VEP cache already extracted"
    fi

    # Upload to S3
    print_info "Uploading VEP cache to S3 (this may take 15-20 minutes)..."
    aws s3 cp homo_sapiens_vep_111_GRCh38.tar.gz "s3://${VEP_CACHE_BUCKET}/cache/"
    aws s3 sync homo_sapiens/ "s3://${VEP_CACHE_BUCKET}/cache/homo_sapiens/"
    print_success "VEP cache uploaded to S3"

    save_config
    print_success "Step 1 Complete: VEP cache setup finished"
}

# Step 2: VEP Docker Setup
setup_vep_docker() {
    print_step "2" "Setting up VEP Docker Container"

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker to continue."
        return 1
    fi

    # Create ECR repository
    print_info "Creating ECR repository: ${ECR_REPOSITORY_NAME}"
    if ! aws ecr describe-repositories --repository-names "${ECR_REPOSITORY_NAME}" --region ${AWS_REGION} &> /dev/null; then
        aws ecr create-repository \
            --repository-name "${ECR_REPOSITORY_NAME}" \
            --region ${AWS_REGION} \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256
        print_success "ECR repository created"
    else
        print_warning "ECR repository already exists"
    fi

    # Login to ECR
    print_info "Logging into ECR..."
    aws ecr get-login-password --region ${AWS_REGION} | \
        docker login --username AWS --password-stdin \
        "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    print_success "Logged into ECR"

    # Pull VEP image (force linux/amd64 - HealthOmics only supports x86_64)
    print_info "Pulling VEP Docker image for linux/amd64 (this may take 5-10 minutes)..."
    docker pull --platform linux/amd64 ensemblorg/ensembl-vep:${VEP_VERSION}
    print_success "VEP image pulled (amd64)"

    # Tag image
    print_info "Tagging image for ECR..."
    docker tag ensemblorg/ensembl-vep:${VEP_VERSION} \
        "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:${VEP_VERSION}"
    print_success "Image tagged"

    # Push to ECR
    print_info "Pushing image to ECR (this may take 5-10 minutes)..."
    docker push "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:${VEP_VERSION}"
    print_success "Image pushed to ECR"

    save_config
    print_success "Step 2 Complete: VEP Docker setup finished"
}

# Step 3: ClinVar Data Setup
setup_clinvar_data() {
    print_step "3" "Setting up ClinVar Annotation Data"

    # Create S3 bucket for ClinVar
    print_info "Creating S3 bucket: ${CLINVAR_BUCKET}"
    if aws s3 ls "s3://${CLINVAR_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://${CLINVAR_BUCKET}" --region ${AWS_REGION}

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${CLINVAR_BUCKET}" \
            --versioning-configuration Status=Enabled

        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "${CLINVAR_BUCKET}" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
        print_success "Bucket created: ${CLINVAR_BUCKET}"
    else
        print_warning "Bucket already exists: ${CLINVAR_BUCKET}"
    fi

    # Download ClinVar (latest version)
    CLINVAR_FILE="clinvar_20260315.vcf.gz"
    print_info "Downloading ClinVar data (this may take 10-15 minutes)..."
    if [ ! -f "${CLINVAR_FILE}" ]; then
        wget https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/${CLINVAR_FILE}
        print_success "ClinVar data downloaded"
    else
        print_warning "ClinVar data already downloaded"
    fi

    # Upload to S3
    print_info "Uploading ClinVar data to S3..."
    aws s3 cp ${CLINVAR_FILE} "s3://${CLINVAR_BUCKET}/clinvar/"
    print_success "ClinVar data uploaded to S3"

    save_config
    print_success "Step 3 Complete: ClinVar setup finished"
}

# Step 4: HealthOmics Reference Store Setup
setup_reference_store() {
    print_step "4" "Setting up HealthOmics Reference Store"

    # Check if reference store exists
    print_info "Checking for existing reference stores..."
    EXISTING_STORE=$(aws omics list-reference-stores --region ${AWS_REGION} --query "referenceStores[?name=='${REFERENCE_STORE_NAME}'].id" --output text 2>/dev/null || echo "")

    # Handle None or empty values
    if [ -z "${EXISTING_STORE}" ] || [ "${EXISTING_STORE}" == "None" ]; then
        print_info "Creating reference store: ${REFERENCE_STORE_NAME}"
        REFERENCE_STORE_ID=$(aws omics create-reference-store \
            --name "${REFERENCE_STORE_NAME}" \
            --description "Reference store for genomic variant analysis" \
            --region ${AWS_REGION} \
            --query 'id' \
            --output text 2>&1)

        # Check if creation was successful
        if [ $? -ne 0 ] || [ -z "${REFERENCE_STORE_ID}" ] || [ "${REFERENCE_STORE_ID}" == "None" ]; then
            print_error "Failed to create reference store"
            print_error "Error: ${REFERENCE_STORE_ID}"
            return 1
        fi

        # Validate the ID format (should be at least 10 characters)
        if [ ${#REFERENCE_STORE_ID} -lt 10 ]; then
            print_error "Invalid reference store ID: ${REFERENCE_STORE_ID}"
            return 1
        fi

        print_success "Reference store created: ${REFERENCE_STORE_ID}"
    else
        REFERENCE_STORE_ID="${EXISTING_STORE}"
        print_warning "Reference store already exists: ${REFERENCE_STORE_ID}"
    fi

    export REFERENCE_STORE_ID
    print_info "Reference Store ID: ${REFERENCE_STORE_ID}"

    # Download reference genome
    print_info "Downloading reference genome (this may take 30-45 minutes)..."
    if [ ! -f "hg38_alt_aware_nohla.fa" ]; then
        aws s3 cp s3://1000genomes-dragen/reference/hg38_alt_aware_nohla.fa .
        print_success "Reference genome downloaded"
    else
        print_warning "Reference genome already downloaded"
    fi

    # Create temporary bucket for reference import
    TEMP_REF_BUCKET="genomics-ref-temp-${AWS_ACCOUNT_ID}-${AWS_REGION}"
    print_info "Creating temporary S3 bucket for reference import: ${TEMP_REF_BUCKET}"
    if aws s3 ls "s3://${TEMP_REF_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://${TEMP_REF_BUCKET}" --region ${AWS_REGION}
    fi

    # Upload reference to S3
    print_info "Uploading reference genome to S3..."
    aws s3 cp hg38_alt_aware_nohla.fa "s3://${TEMP_REF_BUCKET}/reference/"
    print_success "Reference genome uploaded"

    # Create IAM role for HealthOmics (if not exists)
    print_info "Setting up IAM role for HealthOmics..."
    OMICS_ROLE_NAME="HealthOmicsServiceRole"

    if ! aws iam get-role --role-name "${OMICS_ROLE_NAME}" &> /dev/null; then
        # Create trust policy
        cat > /tmp/omics-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "omics.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

        # Create role
        aws iam create-role \
            --role-name "${OMICS_ROLE_NAME}" \
            --assume-role-policy-document file:///tmp/omics-trust-policy.json

        # Attach policies
        aws iam attach-role-policy \
            --role-name "${OMICS_ROLE_NAME}" \
            --policy-arn "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"

        print_success "IAM role created: ${OMICS_ROLE_NAME}"

        # Wait for role to propagate
        print_info "Waiting for IAM role to propagate (30 seconds)..."
        sleep 30

        rm -f /tmp/omics-trust-policy.json
    else
        print_warning "IAM role already exists: ${OMICS_ROLE_NAME}"
    fi

    OMICS_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${OMICS_ROLE_NAME}"

    # Import reference
    print_info "Starting reference import job (this may take 1-2 hours)..."
    IMPORT_JOB_ID=$(aws omics start-reference-import-job \
        --reference-store-id "${REFERENCE_STORE_ID}" \
        --role-arn "${OMICS_ROLE_ARN}" \
        --sources "sourceFile=s3://${TEMP_REF_BUCKET}/reference/hg38_alt_aware_nohla.fa,name=GRCh38,description=Human reference genome GRCh38" \
        --region ${AWS_REGION} \
        --query 'id' \
        --output text)

    print_success "Reference import job started: ${IMPORT_JOB_ID}"
    print_warning "Note: Reference import will continue in the background"
    print_info "Check status with: aws omics get-reference-import-job --reference-store-id ${REFERENCE_STORE_ID} --id ${IMPORT_JOB_ID} --region ${AWS_REGION}"

    save_config
    print_success "Step 4 Complete: Reference store setup initiated"
}

# ============================================================================
# S3 TABLES DEPLOYMENT STEPS (Steps 5-12)
# ============================================================================

# Step 5: Deploy Infrastructure
deploy_infrastructure() {
    print_step "5" "Deploying S3 Tables Infrastructure"

    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} &> /dev/null; then
        print_warning "Stack '${STACK_NAME}' already exists"
        read -p "Update existing stack? (y/n): " update_stack

        if [[ "$update_stack" =~ ^[Yy]$ ]]; then
            print_info "Updating stack..."
            aws cloudformation deploy \
                --template-file "${SCRIPT_DIR}/infrastructure.yaml" \
                --stack-name ${STACK_NAME} \
                --capabilities CAPABILITY_NAMED_IAM \
                --parameter-overrides \
                    ProjectName=${STACK_NAME} \
                    VcfInputBucketName=genomics-vcf-input-v3 \
                    VepOutputBucketName=genomics-vep-output-v3 \
                    BatchSize=20 \
                --region ${AWS_REGION}

            print_success "Stack updated"
        else
            print_info "Skipping stack deployment"
        fi
    else
        print_info "Creating CloudFormation stack: ${STACK_NAME}"

        aws cloudformation deploy \
            --template-file "${SCRIPT_DIR}/infrastructure.yaml" \
            --stack-name ${STACK_NAME} \
            --capabilities CAPABILITY_NAMED_IAM \
            --parameter-overrides \
                ProjectName=${STACK_NAME} \
                VcfInputBucketName=genomics-vcf-input-v3 \
                VepOutputBucketName=genomics-vep-output-v3 \
                BatchSize=20 \
            --region ${AWS_REGION}

        print_info "Waiting for stack creation..."
        aws cloudformation wait stack-create-complete \
            --stack-name ${STACK_NAME} \
            --region ${AWS_REGION}

        print_success "Stack created successfully"
    fi

    # Get stack outputs
    print_info "Retrieving stack outputs..."

    export VCF_INPUT_BUCKET=$(aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${AWS_REGION} \
        --query 'Stacks[0].Outputs[?OutputKey==`VcfInputBucketName`].OutputValue' \
        --output text)

    export VEP_OUTPUT_BUCKET=$(aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${AWS_REGION} \
        --query 'Stacks[0].Outputs[?OutputKey==`VepOutputBucketName`].OutputValue' \
        --output text)

    export DYNAMODB_TABLE=$(aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${AWS_REGION} \
        --query 'Stacks[0].Outputs[?OutputKey==`DynamoTableName`].OutputValue' \
        --output text)

    export LAMBDA_ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${AWS_REGION} \
        --query 'Stacks[0].Outputs[?OutputKey==`LambdaExecutionRoleArn`].OutputValue' \
        --output text)

    export OMICS_ROLE_ARN=$(aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${AWS_REGION} \
        --query 'Stacks[0].Outputs[?OutputKey==`HealthOmicsWorkflowRoleArn`].OutputValue' \
        --output text)

    print_success "Stack outputs retrieved"
    print_info "VCF Input Bucket: ${VCF_INPUT_BUCKET}"
    print_info "VEP Output Bucket: ${VEP_OUTPUT_BUCKET}"
    print_info "DynamoDB Table: ${DYNAMODB_TABLE}"

    save_config
    print_success "Step 5 Complete: Infrastructure deployed"
}

# Step 6: Install Dependencies
install_dependencies() {
    print_step "6" "Installing Python Dependencies"

    cd "${SCRIPT_DIR}"

    # Check if virtual environment exists
    if [ -d ".venv" ]; then
        print_info "Virtual environment exists"
        read -p "Recreate virtual environment? (y/n): " recreate_venv
        if [[ "$recreate_venv" =~ ^[Yy]$ ]]; then
            rm -rf .venv
        fi
    fi

    if [ ! -d ".venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv .venv
        print_success "Virtual environment created"
    fi

    print_info "Activating virtual environment..."
    source .venv/bin/activate

    print_info "Installing dependencies..."
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt

    print_success "Dependencies installed"
    print_warning "Virtual environment activated. Run 'source .venv/bin/activate' to use it."
    print_success "Step 6 Complete: Dependencies installed"
}

# Step 7: Create S3 Tables
create_s3_tables() {
    print_step "7" "Creating S3 Tables Catalog and Schema"

    print_warning "S3 Tables bucket must be created manually via AWS Console first!"
    print_info "Go to: AWS Console → S3 Tables → Create table bucket"
    print_info "Bucket name: genomics-variant-tables-${AWS_ACCOUNT_ID}"
    print_info "Region: ${AWS_REGION}"
    echo ""

    read -p "Have you created the S3 Tables bucket? (y/n): " tables_created

    if [[ ! "$tables_created" =~ ^[Yy]$ ]]; then
        print_warning "Please create the S3 Tables bucket first and run this step again"
        return 1
    fi

    read -p "Enter the Table Bucket ARN: " TABLE_BUCKET_ARN
    export TABLE_BUCKET_ARN

    print_info "Creating namespace and tables..."

    python3 << 'PYTHON_SCRIPT'
import os
import sys
from schema_3 import create_schema_tables
from utils import load_s3_tables_catalog

try:
    region = os.environ['AWS_REGION']
    table_bucket_arn = os.environ['TABLE_BUCKET_ARN']
    namespace = 'variant_db_3'

    print(f"Region: {region}")
    print(f"Table Bucket ARN: {table_bucket_arn}")
    print(f"Namespace: {namespace}")

    # Load catalog
    catalog = load_s3_tables_catalog(table_bucket_arn)
    print("✓ Catalog loaded")

    # Create namespace
    try:
        catalog.create_namespace(namespace)
        print(f"✓ Created namespace: {namespace}")
    except Exception as e:
        print(f"⚠ Namespace may already exist: {e}")

    # Create tables
    tables = create_schema_tables(catalog, namespace)
    print(f"✓ Created tables: {list(tables.keys())}")

    print("\n✓ S3 Tables schema created successfully!")
    sys.exit(0)

except Exception as e:
    print(f"✗ Error creating tables: {e}")
    sys.exit(1)
PYTHON_SCRIPT

    if [ $? -eq 0 ]; then
        print_success "S3 Tables created"
        save_config
        print_success "Step 7 Complete: S3 Tables schema created"
    else
        print_error "Failed to create S3 Tables"
        return 1
    fi
}

# Step 8: Deploy HealthOmics Workflow
deploy_workflow() {
    print_step "8" "Deploying HealthOmics VEP Workflow"

    # Upload workflow definition
    print_info "Uploading VEP workflow definition..."
    aws s3 cp "${SCRIPT_DIR}/VEP.zip" "s3://${VEP_OUTPUT_BUCKET}/workflows/"
    print_success "Workflow definition uploaded"

    # Create workflow
    print_info "Creating HealthOmics workflow..."
    WORKFLOW_ID=$(aws omics create-workflow \
        --name "${STACK_NAME}-vep-workflow" \
        --description "VEP annotation workflow for S3 Tables pipeline" \
        --definition-uri "s3://${VEP_OUTPUT_BUCKET}/workflows/VEP.zip" \
        --engine NEXTFLOW \
        --region ${AWS_REGION} \
        --query 'id' \
        --output text)

    export WORKFLOW_ID
    print_success "Workflow created: ${WORKFLOW_ID}"

    save_config
    print_success "Step 8 Complete: HealthOmics workflow deployed"
}

# Step 9: Setup Athena
setup_athena() {
    print_step "9" "Setting Up Athena Analytics"

    WORKGROUP_NAME="genomics-variant-analysis"

    # Check if workgroup exists
    if aws athena get-work-group --work-group ${WORKGROUP_NAME} --region ${AWS_REGION} &> /dev/null; then
        print_info "Athena workgroup already exists"
    else
        print_info "Creating Athena workgroup..."
        aws athena create-work-group \
            --name ${WORKGROUP_NAME} \
            --description "Workgroup for genomic variant analysis" \
            --configuration "ResultConfiguration={
                OutputLocation=s3://${VEP_OUTPUT_BUCKET}/athena-results/
            }" \
            --region ${AWS_REGION}

        print_success "Athena workgroup created"
    fi

    print_info "You can now query data using:"
    print_info "  aws athena start-query-execution --query-string \"SELECT * FROM variant_db_3.genomic_variants_fixed LIMIT 10\" --work-group ${WORKGROUP_NAME} --region ${AWS_REGION}"

    print_success "Step 9 Complete: Athena analytics configured"
}

# ============================================================================
# Deployment Menu and Main Flow
# ============================================================================

show_menu() {
    print_header "Variant S3 Tables Interpreter Agent - Unified Deployment"

    echo "Select deployment step:"
    echo ""
    echo "${CYAN}Prerequisites (Steps 1-4):${NC}"
    echo "  ${GREEN}1)${NC} Setup VEP Cache Files"
    echo "  ${GREEN}2)${NC} Setup VEP Docker Container (requires Docker)"
    echo "  ${GREEN}3)${NC} Setup ClinVar Annotation Data"
    echo "  ${GREEN}4)${NC} Setup HealthOmics Reference Store"
    echo ""
    echo "${CYAN}S3 Tables Deployment (Steps 5-9):${NC}"
    echo "  ${GREEN}5)${NC} Deploy Infrastructure (CloudFormation)"
    echo "  ${GREEN}6)${NC} Install Python Dependencies"
    echo "  ${GREEN}7)${NC} Create S3 Tables Schema"
    echo "  ${GREEN}8)${NC} Deploy HealthOmics Workflow"
    echo "  ${GREEN}9)${NC} Setup Athena Analytics"
    echo ""
    echo "${CYAN}Quick Options:${NC}"
    echo "  ${YELLOW}p)${NC} Run All Prerequisites (Steps 1-4)"
    echo "  ${YELLOW}d)${NC} Run All S3 Tables Deployment (Steps 5-9)"
    echo "  ${YELLOW}a)${NC} Run Complete Deployment (All Steps 1-9)"
    echo ""
    echo "${CYAN}Utilities:${NC}"
    echo "  ${YELLOW}s)${NC} Show Deployment Status"
    echo "  ${YELLOW}c)${NC} Cleanup/Delete Resources"
    echo ""
    echo "  ${RED}0)${NC} Exit"
    echo ""
}

# Run all prerequisites
run_all_prerequisites() {
    print_header "Running All Prerequisites (Steps 1-4)"

    setup_vep_cache
    setup_vep_docker
    setup_clinvar_data
    setup_reference_store

    print_header "Prerequisites Complete!"
    print_success "All prerequisite steps completed"
    print_info "Next: Run S3 Tables deployment (option 'd')"
}

# Run all S3 Tables deployment
run_s3tables_deployment() {
    print_header "Running S3 Tables Deployment (Steps 5-9)"

    deploy_infrastructure
    install_dependencies
    create_s3_tables
    deploy_workflow
    setup_athena

    print_header "S3 Tables Deployment Complete!"
    print_success "All deployment steps completed"
    print_info "You can now load VCF data and query with Athena"
}

# Run complete deployment
run_complete_deployment() {
    print_header "Running Complete Deployment (Steps 1-9)"

    # Prerequisites
    setup_vep_cache
    setup_vep_docker
    setup_clinvar_data
    setup_reference_store

    # S3 Tables Deployment
    deploy_infrastructure
    install_dependencies
    create_s3_tables
    deploy_workflow
    setup_athena

    print_header "Complete Deployment Finished!"
    print_success "All steps completed successfully"
    print_info ""
    print_info "Configuration Summary:"
    print_info "  • VEP Cache: s3://${VEP_CACHE_BUCKET}"
    print_info "  • ClinVar: s3://${CLINVAR_BUCKET}"
    print_info "  • VCF Input: s3://${VCF_INPUT_BUCKET}"
    print_info "  • VEP Output: s3://${VEP_OUTPUT_BUCKET}"
    print_info "  • DynamoDB: ${DYNAMODB_TABLE}"
    print_info "  • S3 Tables: ${TABLE_BUCKET_ARN}"
    print_info "  • Workflow ID: ${WORKFLOW_ID}"
    print_info ""
    print_info "Next Steps:"
    print_info "  1. Load VCF data using: ./load-test-data.sh"
    print_info "  2. Deploy agent using: ./deploy-agent.sh"
    print_info "  3. Query data with Athena or run the Streamlit UI"
}

# Show status
show_status() {
    print_header "Deployment Status"

    load_config

    echo -e "${BLUE}Prerequisites Status:${NC}"
    [ -n "${VEP_CACHE_BUCKET}" ] && echo -e "  VEP Cache: ${GREEN}${VEP_CACHE_BUCKET}${NC}" || echo -e "  VEP Cache: ${RED}NOT SET${NC}"
    [ -n "${CLINVAR_BUCKET}" ] && echo -e "  ClinVar: ${GREEN}${CLINVAR_BUCKET}${NC}" || echo -e "  ClinVar: ${RED}NOT SET${NC}"
    [ -n "${ECR_REPOSITORY_NAME}" ] && echo -e "  ECR Repo: ${GREEN}${ECR_REPOSITORY_NAME}${NC}" || echo -e "  ECR Repo: ${RED}NOT SET${NC}"
    [ -n "${REFERENCE_STORE_ID}" ] && echo -e "  Reference Store: ${GREEN}${REFERENCE_STORE_ID}${NC}" || echo -e "  Reference Store: ${RED}NOT SET${NC}"

    echo -e "\n${BLUE}CloudFormation Stack:${NC}"
    if aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} &> /dev/null; then
        STATUS=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query 'Stacks[0].StackStatus' --output text)
        echo -e "  ${GREEN}${STACK_NAME}: ${STATUS}${NC}"
    else
        echo -e "  ${RED}${STACK_NAME}: NOT FOUND${NC}"
    fi

    echo -e "\n${BLUE}S3 Tables Resources:${NC}"
    [ -n "${VCF_INPUT_BUCKET}" ] && echo -e "  S3 Input: ${GREEN}${VCF_INPUT_BUCKET}${NC}" || echo -e "  S3 Input: ${RED}NOT SET${NC}"
    [ -n "${VEP_OUTPUT_BUCKET}" ] && echo -e "  S3 Output: ${GREEN}${VEP_OUTPUT_BUCKET}${NC}" || echo -e "  S3 Output: ${RED}NOT SET${NC}"
    [ -n "${DYNAMODB_TABLE}" ] && echo -e "  DynamoDB: ${GREEN}${DYNAMODB_TABLE}${NC}" || echo -e "  DynamoDB: ${RED}NOT SET${NC}"
    [ -n "${TABLE_BUCKET_ARN}" ] && echo -e "  S3 Tables: ${GREEN}${TABLE_BUCKET_ARN}${NC}" || echo -e "  S3 Tables: ${RED}NOT SET${NC}"
    [ -n "${WORKFLOW_ID}" ] && echo -e "  Workflow: ${GREEN}${WORKFLOW_ID}${NC}" || echo -e "  Workflow: ${RED}NOT SET${NC}"
}

# Cleanup
cleanup() {
    print_header "Cleanup Resources"

    print_error "WARNING: This will delete ALL resources!"
    read -p "Type 'DELETE' to confirm: " confirm

    if [ "$confirm" != "DELETE" ]; then
        print_info "Cleanup cancelled"
        return 0
    fi

    load_config

    # Delete CloudFormation stack
    print_info "Deleting CloudFormation stack..."
    aws cloudformation delete-stack \
        --stack-name ${STACK_NAME} \
        --region ${AWS_REGION}

    print_info "Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete \
        --stack-name ${STACK_NAME} \
        --region ${AWS_REGION}

    # Delete S3 buckets (prerequisites)
    if [ -n "${VEP_CACHE_BUCKET}" ]; then
        print_info "Deleting VEP cache bucket..."
        aws s3 rb "s3://${VEP_CACHE_BUCKET}" --force 2> /dev/null || true
    fi

    if [ -n "${CLINVAR_BUCKET}" ]; then
        print_info "Deleting ClinVar bucket..."
        aws s3 rb "s3://${CLINVAR_BUCKET}" --force 2> /dev/null || true
    fi

    # Delete ECR repository
    if [ -n "${ECR_REPOSITORY_NAME}" ]; then
        print_info "Deleting ECR repository..."
        aws ecr delete-repository \
            --repository-name "${ECR_REPOSITORY_NAME}" \
            --force \
            --region ${AWS_REGION} 2> /dev/null || true
    fi

    # Remove config file
    rm -f "${CONFIG_FILE}"

    print_success "Cleanup complete"
    print_warning "Note: S3 Tables and Reference Store must be deleted manually via AWS Console"
}

# Main execution
main() {
    check_prerequisites
    load_config

    if [ $# -eq 0 ]; then
        # Interactive mode
        while true; do
            show_menu
            read -p "Enter your choice: " choice

            case $choice in
                1) setup_vep_cache ;;
                2) setup_vep_docker ;;
                3) setup_clinvar_data ;;
                4) setup_reference_store ;;
                5) deploy_infrastructure ;;
                6) install_dependencies ;;
                7) create_s3_tables ;;
                8) deploy_workflow ;;
                9) setup_athena ;;
                p|P) run_all_prerequisites ;;
                d|D) run_s3tables_deployment ;;
                a|A) run_complete_deployment ;;
                s|S) show_status ;;
                c|C) cleanup ;;
                0) print_info "Exiting..."; exit 0 ;;
                *) print_error "Invalid choice" ;;
            esac

            echo ""
            read -p "Press Enter to continue..."
        done
    else
        # Command-line mode
        case $1 in
            prerequisites) run_all_prerequisites ;;
            deploy) run_s3tables_deployment ;;
            full) run_complete_deployment ;;
            status) show_status ;;
            cleanup) cleanup ;;
            *)
                echo "Usage: $0 [prerequisites|deploy|full|status|cleanup]"
                echo "  prerequisites - Run prerequisites setup (steps 1-4)"
                echo "  deploy        - Run S3 Tables deployment (steps 5-9)"
                echo "  full          - Run complete deployment (all steps)"
                echo "  status        - Show deployment status"
                echo "  cleanup       - Delete all resources"
                exit 1
                ;;
        esac
    fi
}

# Run main
main "$@"
