#!/bin/bash

# ============================================================================
# Variant S3 Tables Interpreter Agent - Pipeline Orchestration Deployment
# ============================================================================
# This script deploys the event-driven pipeline orchestration layer
# Prerequisites: Run deploy-unified.sh steps 1-9 first
# Region: us-west-2
# Version: 1.0
# ============================================================================

set -e  # Exit on error

# Add AWS CLI to PATH
export PATH="/usr/local/bin:$PATH"

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
ORCHESTRATION_CONFIG="${SCRIPT_DIR}/orchestration-config.env"

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

    # Check if deployment-config.env exists
    if [ ! -f "${CONFIG_FILE}" ]; then
        print_error "Deployment config not found: ${CONFIG_FILE}"
        print_error "Please run deploy-unified.sh first to complete steps 1-9"
        exit 1
    fi

    # Load configuration
    source "${CONFIG_FILE}"

    # Verify required variables
    local missing=0

    if [ -z "${AWS_ACCOUNT_ID}" ]; then print_error "AWS_ACCOUNT_ID not set"; missing=1; fi
    if [ -z "${AWS_REGION}" ]; then print_error "AWS_REGION not set"; missing=1; fi
    if [ -z "${VCF_INPUT_BUCKET}" ]; then print_error "VCF_INPUT_BUCKET not set"; missing=1; fi
    if [ -z "${VEP_OUTPUT_BUCKET}" ]; then print_error "VEP_OUTPUT_BUCKET not set"; missing=1; fi
    if [ -z "${DYNAMODB_TABLE}" ]; then print_error "DYNAMODB_TABLE not set"; missing=1; fi
    if [ -z "${WORKFLOW_ID}" ]; then print_error "WORKFLOW_ID not set"; missing=1; fi
    if [ -z "${OMICS_ROLE_ARN}" ]; then print_error "OMICS_ROLE_ARN not set"; missing=1; fi
    if [ -z "${TABLE_BUCKET_ARN}" ]; then print_error "TABLE_BUCKET_ARN not set"; missing=1; fi

    if [ $missing -eq 1 ]; then
        print_error "Missing required configuration. Please run deploy-unified.sh first."
        exit 1
    fi

    print_success "All prerequisites validated"
    print_info "AWS Account: ${AWS_ACCOUNT_ID}"
    print_info "Region: ${AWS_REGION}"
    print_info "Stack: ${STACK_NAME}"
}

# Load orchestration configuration
load_orchestration_config() {
    if [ -f "${ORCHESTRATION_CONFIG}" ]; then
        print_info "Loading orchestration configuration..."
        source "${ORCHESTRATION_CONFIG}"
    fi
}

# Save orchestration configuration
save_orchestration_config() {
    print_info "Saving orchestration configuration..."
    cat > "${ORCHESTRATION_CONFIG}" << EOF
# Pipeline Orchestration Configuration
# Generated on $(date)

# AWS Batch Resources
BATCH_SERVICE_ROLE_ARN=${BATCH_SERVICE_ROLE_ARN:-}
BATCH_EXECUTION_ROLE_ARN=${BATCH_EXECUTION_ROLE_ARN:-}
BATCH_TASK_ROLE_ARN=${BATCH_TASK_ROLE_ARN:-}
BATCH_COMPUTE_ENV_NAME=${BATCH_COMPUTE_ENV_NAME:-}
BATCH_JOB_QUEUE_NAME=${BATCH_JOB_QUEUE_NAME:-}
BATCH_JOB_DEFINITION_NAME=${BATCH_JOB_DEFINITION_NAME:-}

# Step Functions
STEP_FUNCTION_ROLE_ARN=${STEP_FUNCTION_ROLE_ARN:-}
STATE_MACHINE_ARN=${STATE_MACHINE_ARN:-}

# Lambda Functions
WORKFLOW_TRIGGER_LAMBDA_ARN=${WORKFLOW_TRIGGER_LAMBDA_ARN:-}
S3TABLES_IMPORT_LAMBDA_ARN=${S3TABLES_IMPORT_LAMBDA_ARN:-}

# EventBridge
EVENTBRIDGE_RULE_ARN=${EVENTBRIDGE_RULE_ARN:-}
EOF
    print_success "Orchestration configuration saved"
}

# ============================================================================
# Step 10: Create AWS Batch Infrastructure
# ============================================================================

create_batch_infrastructure() {
    print_step "10" "Creating AWS Batch Infrastructure"

    # Create Batch Service Role
    print_info "Creating AWS Batch service role..."

    BATCH_SERVICE_ROLE_NAME="${STACK_NAME}-batch-service-role"

    if ! aws iam get-role --role-name "${BATCH_SERVICE_ROLE_NAME}" &> /dev/null; then
        cat > /tmp/batch-service-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "batch.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

        aws iam create-role \
            --role-name "${BATCH_SERVICE_ROLE_NAME}" \
            --assume-role-policy-document file:///tmp/batch-service-trust-policy.json

        aws iam attach-role-policy \
            --role-name "${BATCH_SERVICE_ROLE_NAME}" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"

        print_success "Batch service role created"
        sleep 10  # Wait for role propagation
        rm -f /tmp/batch-service-trust-policy.json
    else
        print_warning "Batch service role already exists"
    fi

    export BATCH_SERVICE_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${BATCH_SERVICE_ROLE_NAME}"

    # Create Batch Execution Role
    print_info "Creating AWS Batch execution role..."

    BATCH_EXECUTION_ROLE_NAME="${STACK_NAME}-batch-execution-role"

    if ! aws iam get-role --role-name "${BATCH_EXECUTION_ROLE_NAME}" &> /dev/null; then
        cat > /tmp/batch-execution-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

        aws iam create-role \
            --role-name "${BATCH_EXECUTION_ROLE_NAME}" \
            --assume-role-policy-document file:///tmp/batch-execution-trust-policy.json

        aws iam attach-role-policy \
            --role-name "${BATCH_EXECUTION_ROLE_NAME}" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"

        print_success "Batch execution role created"
        sleep 10
        rm -f /tmp/batch-execution-trust-policy.json
    else
        print_warning "Batch execution role already exists"
    fi

    export BATCH_EXECUTION_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${BATCH_EXECUTION_ROLE_NAME}"

    # Create Batch Task Role
    print_info "Creating AWS Batch task role..."

    BATCH_TASK_ROLE_NAME="${STACK_NAME}-batch-task-role"

    if ! aws iam get-role --role-name "${BATCH_TASK_ROLE_NAME}" &> /dev/null; then
        cat > /tmp/batch-task-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

        aws iam create-role \
            --role-name "${BATCH_TASK_ROLE_NAME}" \
            --assume-role-policy-document file:///tmp/batch-task-trust-policy.json

        # Create inline policy for S3 Tables and DynamoDB access
        cat > /tmp/batch-task-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${VEP_OUTPUT_BUCKET}",
        "arn:aws:s3:::${VEP_OUTPUT_BUCKET}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3tables:GetTableBucket",
        "s3tables:GetTable",
        "s3tables:PutTableData",
        "s3tables:GetTableData"
      ],
      "Resource": "${TABLE_BUCKET_ARN}/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"      ],
      "Resource": "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/${DYNAMODB_TABLE}"
    }
  ]
}
EOF

        aws iam put-role-policy \
            --role-name "${BATCH_TASK_ROLE_NAME}" \
            --policy-name "S3TablesAndDynamoDBAccess" \
            --policy-document file:///tmp/batch-task-policy.json

        print_success "Batch task role created"
        sleep 10
        rm -f /tmp/batch-task-trust-policy.json
        rm -f /tmp/batch-task-policy.json
    else
        print_warning "Batch task role already exists"
    fi

    export BATCH_TASK_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${BATCH_TASK_ROLE_NAME}"

    # Create Compute Environment
    print_info "Creating AWS Batch compute environment..."

    export BATCH_COMPUTE_ENV_NAME="${STACK_NAME}-compute-env"

    # Check if compute environment actually exists (not just if the API call succeeds)
    EXISTING_COMPUTE_ENV=$(aws batch describe-compute-environments \
        --compute-environments "${BATCH_COMPUTE_ENV_NAME}" \
        --region ${AWS_REGION} \
        --query 'computeEnvironments[0].computeEnvironmentName' \
        --output text 2>/dev/null || echo "None")

    if [ "${EXISTING_COMPUTE_ENV}" = "None" ] || [ -z "${EXISTING_COMPUTE_ENV}" ]; then

        # Get default VPC
        print_info "Getting VPC configuration..."
        DEFAULT_VPC_ID=$(aws ec2 describe-vpcs \
            --filters "Name=is-default,Values=true" \
            --query 'Vpcs[0].VpcId' \
            --region ${AWS_REGION} \
            --output text)

        if [ -z "${DEFAULT_VPC_ID}" ] || [ "${DEFAULT_VPC_ID}" = "None" ]; then
            print_error "No default VPC found. Batch requires VPC configuration."
            print_error "Please create a VPC or specify VPC/subnet/security group IDs manually."
            return 1
        fi

        print_info "Using VPC: ${DEFAULT_VPC_ID}"

        # Get subnets in the default VPC
        SUBNET_IDS=$(aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=${DEFAULT_VPC_ID}" \
            --query 'Subnets[*].SubnetId' \
            --region ${AWS_REGION} \
            --output json)

        if [ "${SUBNET_IDS}" = "[]" ]; then
            print_error "No subnets found in VPC ${DEFAULT_VPC_ID}"
            return 1
        fi

        print_info "Found subnets: ${SUBNET_IDS}"

        # Get default security group for this VPC
        SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
            --filters "Name=vpc-id,Values=${DEFAULT_VPC_ID}" "Name=group-name,Values=default" \
            --query 'SecurityGroups[0].GroupId' \
            --region ${AWS_REGION} \
            --output text)

        if [ -z "${SECURITY_GROUP_ID}" ] || [ "${SECURITY_GROUP_ID}" = "None" ]; then
            print_error "No default security group found in VPC ${DEFAULT_VPC_ID}"
            return 1
        fi

        print_info "Using security group: ${SECURITY_GROUP_ID}"

        # Create compute environment with proper VPC configuration
        aws batch create-compute-environment \
            --compute-environment-name "${BATCH_COMPUTE_ENV_NAME}" \
            --type MANAGED \
            --state ENABLED \
            --service-role "${BATCH_SERVICE_ROLE_ARN}" \
            --compute-resources "{
                \"type\": \"FARGATE\",
                \"maxvCpus\": 256,
                \"subnets\": ${SUBNET_IDS},
                \"securityGroupIds\": [\"${SECURITY_GROUP_ID}\"]
            }" \
            --region ${AWS_REGION}

        print_success "Compute environment created"

        # Wait for compute environment to be valid
        print_info "Waiting for compute environment to be ready (this may take 5-10 minutes)..."

        # Poll for status instead of wait (more informative)
        MAX_WAIT=600  # 10 minutes
        ELAPSED=0
        while [ $ELAPSED -lt $MAX_WAIT ]; do
            STATUS=$(aws batch describe-compute-environments \
                --compute-environments "${BATCH_COMPUTE_ENV_NAME}" \
                --region ${AWS_REGION} \
                --query 'computeEnvironments[0].status' \
                --output text)

            if [ "${STATUS}" = "VALID" ]; then
                print_success "Compute environment is ready"
                break
            elif [ "${STATUS}" = "INVALID" ]; then
                STATUS_REASON=$(aws batch describe-compute-environments \
                    --compute-environments "${BATCH_COMPUTE_ENV_NAME}" \
                    --region ${AWS_REGION} \
                    --query 'computeEnvironments[0].statusReason' \
                    --output text)
                print_error "Compute environment became INVALID: ${STATUS_REASON}"
                return 1
            fi

            sleep 10
            ELAPSED=$((ELAPSED + 10))
            echo -n "."
        done

        if [ $ELAPSED -ge $MAX_WAIT ]; then
            print_error "Timeout waiting for compute environment to become ready"
            return 1
        fi
    else
        print_warning "Compute environment already exists"
    fi

    # Create Job Queue
    print_info "Creating AWS Batch job queue..."

    export BATCH_JOB_QUEUE_NAME="${STACK_NAME}-job-queue"

    # Check if job queue actually exists
    EXISTING_JOB_QUEUE=$(aws batch describe-job-queues \
        --job-queues "${BATCH_JOB_QUEUE_NAME}" \
        --region ${AWS_REGION} \
        --query 'jobQueues[0].jobQueueName' \
        --output text 2>/dev/null || echo "None")

    if [ "${EXISTING_JOB_QUEUE}" = "None" ] || [ -z "${EXISTING_JOB_QUEUE}" ]; then

        aws batch create-job-queue \
            --job-queue-name "${BATCH_JOB_QUEUE_NAME}" \
            --state ENABLED \
            --priority 1 \
            --compute-environment-order "order=1,computeEnvironment=${BATCH_COMPUTE_ENV_NAME}" \
            --region ${AWS_REGION}

        print_success "Job queue created"
    else
        print_warning "Job queue already exists"
    fi

    # Create Job Definition
    print_info "Creating AWS Batch job definition..."

    export BATCH_JOB_DEFINITION_NAME="${STACK_NAME}-s3tables-import-job"

    # Check if job definition exists and is active
    EXISTING_JOB_DEF=$(aws batch describe-job-definitions \
        --job-definition-name "${BATCH_JOB_DEFINITION_NAME}" \
        --status ACTIVE \
        --region ${AWS_REGION} \
        --query 'jobDefinitions[0].jobDefinitionName' \
        --output text 2>/dev/null || echo "None")

    # Note: Using a placeholder image - update with actual S3 Tables import container
    cat > /tmp/batch-job-definition.json << EOF
{
  "jobDefinitionName": "${BATCH_JOB_DEFINITION_NAME}",
  "type": "container",
  "platformCapabilities": ["FARGATE"],
  "containerProperties": {
    "image": "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:${VEP_VERSION}",
    "resourceRequirements": [
      {"type": "VCPU", "value": "2"},
      {"type": "MEMORY", "value": "4096"}
    ],
    "executionRoleArn": "${BATCH_EXECUTION_ROLE_ARN}",
    "jobRoleArn": "${BATCH_TASK_ROLE_ARN}",
    "environment": [
      {"name": "TABLE_BUCKET_ARN", "value": "${TABLE_BUCKET_ARN}"},
      {"name": "DYNAMODB_TABLE", "value": "${DYNAMODB_TABLE}"},
      {"name": "AWS_REGION", "value": "${AWS_REGION}"}
    ]
  }
}
EOF

    if [ "${EXISTING_JOB_DEF}" = "None" ] || [ -z "${EXISTING_JOB_DEF}" ]; then

        aws batch register-job-definition \
            --cli-input-json file:///tmp/batch-job-definition.json \
            --region ${AWS_REGION}

        print_success "Job definition created"
        rm -f /tmp/batch-job-definition.json
    else
        print_warning "Job definition already exists"
    fi

    save_orchestration_config
    print_success "Step 10 Complete: AWS Batch infrastructure created"
}

# ============================================================================
# Step 11: Create Lambda Functions
# ============================================================================

create_lambda_functions() {
    print_step "11" "Creating Lambda Functions"

    cd "${SCRIPT_DIR}"

    # Create Lambda execution role
    print_info "Creating Lambda execution role..."

    LAMBDA_ORCHESTRATION_ROLE_NAME="${STACK_NAME}-lambda-orchestration-role"

    if ! aws iam get-role --role-name "${LAMBDA_ORCHESTRATION_ROLE_NAME}" &> /dev/null; then
        cat > /tmp/lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

        aws iam create-role \
            --role-name "${LAMBDA_ORCHESTRATION_ROLE_NAME}" \
            --assume-role-policy-document file:///tmp/lambda-trust-policy.json

        # Attach policies
        aws iam attach-role-policy \
            --role-name "${LAMBDA_ORCHESTRATION_ROLE_NAME}" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

        # Create custom policy
        cat > /tmp/lambda-custom-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "omics:StartRun",
        "omics:GetRun",
        "omics:ListRuns"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${VCF_INPUT_BUCKET}",
        "arn:aws:s3:::${VCF_INPUT_BUCKET}/*",
        "arn:aws:s3:::${VEP_OUTPUT_BUCKET}",
        "arn:aws:s3:::${VEP_OUTPUT_BUCKET}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/${DYNAMODB_TABLE}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3tables:GetTableBucket",
        "s3tables:GetTable",
        "s3tables:PutTableData"
      ],
      "Resource": "${TABLE_BUCKET_ARN}/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "batch:SubmitJob",
        "batch:DescribeJobs"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "${OMICS_ROLE_ARN}",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "omics.amazonaws.com"
        }
      }
    }
  ]
}
EOF

        aws iam put-role-policy \
            --role-name "${LAMBDA_ORCHESTRATION_ROLE_NAME}" \
            --policy-name "OmicsS3TablesAccess" \
            --policy-document file:///tmp/lambda-custom-policy.json

        print_success "Lambda execution role created"
        sleep 15  # Wait for role propagation
        rm -f /tmp/lambda-trust-policy.json
        rm -f /tmp/lambda-custom-policy.json
    else
        print_warning "Lambda execution role already exists"
    fi

    LAMBDA_ORCHESTRATION_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ORCHESTRATION_ROLE_NAME}"

    # Create Workflow Trigger Lambda
    print_info "Creating workflow trigger Lambda function..."

    mkdir -p /tmp/lambda-workflow-trigger
    cat > /tmp/lambda-workflow-trigger/lambda_function.py << 'LAMBDA_CODE'
import json
import boto3
import os
from datetime import datetime

omics = boto3.client('omics')
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

WORKFLOW_ID = os.environ['WORKFLOW_ID']
OMICS_ROLE_ARN = os.environ['OMICS_ROLE_ARN']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
VEP_OUTPUT_BUCKET = os.environ['VEP_OUTPUT_BUCKET']
VEP_CACHE_BUCKET = os.environ['VEP_CACHE_BUCKET']
REFERENCE_STORE_ID = os.environ['REFERENCE_STORE_ID']
AWS_ACCOUNT_ID = os.environ['AWS_ACCOUNT_ID']

def lambda_handler(event, context):
    # Construct ECR registry URL from context
    region = context.invoked_function_arn.split(':')[3]
    ecr_registry = f"{AWS_ACCOUNT_ID}.dkr.ecr.{region}.amazonaws.com"

    print(f"Event received: {json.dumps(event)}")

    table = dynamodb.Table(DYNAMODB_TABLE)

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        print(f"Processing: s3://{bucket}/{key}")

        # Only process VCF files
        if not (key.endswith('.vcf') or key.endswith('.vcf.gz')):
            print(f"Skipping non-VCF file: {key}")
            continue

        # Extract sample ID from filename
        sample_id = key.split('/')[-1].replace('.vcf.gz', '').replace('.vcf', '')

        try:
            # Start HealthOmics workflow with correct parameters
            run_response = omics.start_run(
                workflowId=WORKFLOW_ID,
                roleArn=OMICS_ROLE_ARN,
                name=f"vep-{sample_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                parameters={
                    'id': sample_id,
                    'vcf': f"s3://{bucket}/{key}",
                    'vep_species': 'homo_sapiens',
                    'vep_cache': f"s3://{VEP_CACHE_BUCKET}/cache/",
                    'vep_cache_version': '113',
                    'vep_genome': 'GRCh38',
                    'ecr_registry': ecr_registry
                },
                outputUri=f"s3://{VEP_OUTPUT_BUCKET}/output/{sample_id}/"
            )

            run_id = run_response['id']
            print(f"Started run: {run_id}")

            # Update DynamoDB with correct schema
            table.put_item(
                Item={
                    'SampleID': sample_id,
                    'ProcessingStage': 'workflow_running',
                    'RunID': run_id,
                    'Status': 'RUNNING',
                    'InputVCF': f"s3://{bucket}/{key}",
                    'OutputPrefix': f"s3://{VEP_OUTPUT_BUCKET}/output/{sample_id}",
                    'CreatedAt': datetime.now().isoformat(),
                    'UpdatedAt': datetime.now().isoformat(),
                    'WorkflowID': WORKFLOW_ID
                }
            )

            print(f"DynamoDB updated for sample: {sample_id}")

        except Exception as e:
            print(f"Error processing {key}: {str(e)}")
            raise

    return {
        'statusCode': 200,
        'body': json.dumps('Workflow triggered successfully')
    }
LAMBDA_CODE

    cd /tmp/lambda-workflow-trigger
    zip -q lambda-workflow-trigger.zip lambda_function.py

    WORKFLOW_TRIGGER_LAMBDA_NAME="${STACK_NAME}-workflow-trigger"

    if ! aws lambda get-function --function-name "${WORKFLOW_TRIGGER_LAMBDA_NAME}" --region ${AWS_REGION} &> /dev/null; then
        aws lambda create-function \
            --function-name "${WORKFLOW_TRIGGER_LAMBDA_NAME}" \
            --runtime python3.11 \
            --role "${LAMBDA_ORCHESTRATION_ROLE_ARN}" \
            --handler lambda_function.lambda_handler \
            --zip-file fileb://lambda-workflow-trigger.zip \
            --timeout 60 \
            --memory-size 256 \
            --environment "Variables={
                WORKFLOW_ID=${WORKFLOW_ID},
                OMICS_ROLE_ARN=${OMICS_ROLE_ARN},
                DYNAMODB_TABLE=${DYNAMODB_TABLE},
                VEP_OUTPUT_BUCKET=${VEP_OUTPUT_BUCKET},
                VEP_CACHE_BUCKET=${VEP_CACHE_BUCKET},
                REFERENCE_STORE_ID=${REFERENCE_STORE_ID},
                AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
            }" \
            --region ${AWS_REGION}

        print_success "Workflow trigger Lambda created"
    else
        print_warning "Workflow trigger Lambda already exists - updating code..."
        aws lambda update-function-code \
            --function-name "${WORKFLOW_TRIGGER_LAMBDA_NAME}" \
            --zip-file fileb://lambda-workflow-trigger.zip \
            --region ${AWS_REGION}

        # Update environment variables
        aws lambda update-function-configuration \
            --function-name "${WORKFLOW_TRIGGER_LAMBDA_NAME}" \
            --environment "Variables={
                WORKFLOW_ID=${WORKFLOW_ID},
                OMICS_ROLE_ARN=${OMICS_ROLE_ARN},
                DYNAMODB_TABLE=${DYNAMODB_TABLE},
                VEP_OUTPUT_BUCKET=${VEP_OUTPUT_BUCKET},
                VEP_CACHE_BUCKET=${VEP_CACHE_BUCKET},
                REFERENCE_STORE_ID=${REFERENCE_STORE_ID},
                AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
            }" \
            --region ${AWS_REGION}
    fi

    export WORKFLOW_TRIGGER_LAMBDA_ARN=$(aws lambda get-function \
        --function-name "${WORKFLOW_TRIGGER_LAMBDA_NAME}" \
        --region ${AWS_REGION} \
        --query 'Configuration.FunctionArn' \
        --output text)

    # Create S3 Tables Import Lambda
    print_info "Creating S3 Tables import Lambda function..."

    mkdir -p /tmp/lambda-s3tables-import
    cat > /tmp/lambda-s3tables-import/lambda_function.py << 'LAMBDA_CODE'
import json
import boto3
import os
from datetime import datetime

batch = boto3.client('batch')
dynamodb = boto3.resource('dynamodb')

JOB_QUEUE = os.environ['BATCH_JOB_QUEUE']
JOB_DEFINITION = os.environ['BATCH_JOB_DEFINITION']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']

def lambda_handler(event, context):
    print(f"Event received: {json.dumps(event)}")

    table = dynamodb.Table(DYNAMODB_TABLE)

    # Parse EventBridge event from HealthOmics
    detail = event.get('detail', {})
    run_id = detail.get('runId') or detail.get('id')
    status = detail.get('status')

    print(f"Run ID: {run_id}, Status: {status}")

    if status != 'COMPLETED':
        print(f"Workflow not completed. Status: {status}")
        return {
            'statusCode': 200,
            'body': json.dumps(f'Workflow status: {status}')
        }

    # Get sample info from DynamoDB
    try:
        # Scan for the matching RunID since we may not have a GSI
        response = table.scan(
            FilterExpression='RunID = :rid',
            ExpressionAttributeValues={':rid': run_id}
        )

        if not response.get('Items'):
            print(f"No DynamoDB entry found for RunID: {run_id}")
            # Fallback: submit batch job without sample context
            sample_id = run_id
            output_prefix = detail.get('outputUri', '')
        else:
            item = response['Items'][0]
            sample_id = item['SampleID']
            output_prefix = item.get('OutputPrefix', '')

        # Submit Batch job to import to S3 Tables
        batch_response = batch.submit_job(
            jobName=f"s3tables-import-{sample_id}",
            jobQueue=JOB_QUEUE,
            jobDefinition=JOB_DEFINITION,
            containerOverrides={
                'environment': [
                    {'name': 'SAMPLE_ID', 'value': sample_id},
                    {'name': 'VEP_OUTPUT_PATH', 'value': output_prefix},
                    {'name': 'RUN_ID', 'value': run_id}
                ]
            }
        )

        batch_job_id = batch_response['jobId']
        print(f"Batch job submitted: {batch_job_id}")

        # Update DynamoDB
        table.update_item(
            Key={'SampleID': sample_id},
            UpdateExpression='SET #status = :status, BatchJobID = :job_id, UpdatedAt = :updated',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': 'IMPORTING',
                ':job_id': batch_job_id,
                ':updated': datetime.now().isoformat()
            }
        )

        return {
            'statusCode': 200,
            'body': json.dumps(f'Batch import job started: {batch_job_id}')
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        raise
LAMBDA_CODE

    cd /tmp/lambda-s3tables-import
    zip -q lambda-s3tables-import.zip lambda_function.py

    S3TABLES_IMPORT_LAMBDA_NAME="${STACK_NAME}-s3tables-import"

    if ! aws lambda get-function --function-name "${S3TABLES_IMPORT_LAMBDA_NAME}" --region ${AWS_REGION} &> /dev/null; then
        aws lambda create-function \
            --function-name "${S3TABLES_IMPORT_LAMBDA_NAME}" \
            --runtime python3.11 \
            --role "${LAMBDA_ORCHESTRATION_ROLE_ARN}" \
            --handler lambda_function.lambda_handler \
            --zip-file fileb://lambda-s3tables-import.zip \
            --timeout 60 \
            --memory-size 256 \
            --environment "Variables={
                BATCH_JOB_QUEUE=${BATCH_JOB_QUEUE_NAME},
                BATCH_JOB_DEFINITION=${BATCH_JOB_DEFINITION_NAME},
                DYNAMODB_TABLE=${DYNAMODB_TABLE}
            }" \
            --region ${AWS_REGION}

        print_success "S3 Tables import Lambda created"
    else
        print_warning "S3 Tables import Lambda already exists - updating code..."
        aws lambda update-function-code \
            --function-name "${S3TABLES_IMPORT_LAMBDA_NAME}" \
            --zip-file fileb://lambda-s3tables-import.zip \
            --region ${AWS_REGION}
    fi

    export S3TABLES_IMPORT_LAMBDA_ARN=$(aws lambda get-function \
        --function-name "${S3TABLES_IMPORT_LAMBDA_NAME}" \
        --region ${AWS_REGION} \
        --query 'Configuration.FunctionArn' \
        --output text)

    # Cleanup
    rm -rf /tmp/lambda-workflow-trigger
    rm -rf /tmp/lambda-s3tables-import

    save_orchestration_config
    print_success "Step 11 Complete: Lambda functions created"
}

# ============================================================================
# Step 12: Configure Event-Driven Pipeline
# ============================================================================

configure_event_pipeline() {
    print_step "12" "Configuring Event-Driven Pipeline"

    # Configure S3 event notification for workflow trigger
    print_info "Configuring S3 event notification for input bucket..."

    # Add Lambda permission for S3 to invoke
    aws lambda add-permission \
        --function-name "${WORKFLOW_TRIGGER_LAMBDA_ARN}" \
        --statement-id "S3InvokePermission" \
        --action "lambda:InvokeFunction" \
        --principal s3.amazonaws.com \
        --source-arn "arn:aws:s3:::${VCF_INPUT_BUCKET}" \
        --region ${AWS_REGION} 2>/dev/null || print_warning "S3 permission already exists"

    # Create S3 notification configuration
    cat > /tmp/s3-notification.json << EOF
{
  "LambdaFunctionConfigurations": [
    {
      "Id": "VCFUploadTrigger",
      "LambdaFunctionArn": "${WORKFLOW_TRIGGER_LAMBDA_ARN}",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "suffix",
              "Value": ".vcf.gz"
            }
          ]
        }
      }
    }
  ]
}
EOF

    aws s3api put-bucket-notification-configuration \
        --bucket "${VCF_INPUT_BUCKET}" \
        --notification-configuration file:///tmp/s3-notification.json

    print_success "S3 event notification configured"
    rm -f /tmp/s3-notification.json

    # Create EventBridge rule for workflow completion
    print_info "Creating EventBridge rule for workflow completion..."

    EVENTBRIDGE_RULE_NAME="${STACK_NAME}-workflow-completion"

    aws events put-rule \
        --name "${EVENTBRIDGE_RULE_NAME}" \
        --event-pattern "{
            \"source\": [\"aws.omics\"],
            \"detail-type\": [\"Run Status Change\", \"HealthOmics Run Status Change\"],
            \"detail\": {
                \"status\": [\"COMPLETED\", \"FAILED\"]
            }
        }" \
        --state ENABLED \
        --region ${AWS_REGION}

    print_success "EventBridge rule created"

    # Add Lambda permission for EventBridge
    aws lambda add-permission \
        --function-name "${S3TABLES_IMPORT_LAMBDA_ARN}" \
        --statement-id "EventBridgeInvokePermission" \
        --action "lambda:InvokeFunction" \
        --principal events.amazonaws.com \
        --source-arn "arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/${EVENTBRIDGE_RULE_NAME}" \
        --region ${AWS_REGION} 2>/dev/null || print_warning "EventBridge permission already exists"

    # Add Lambda as target
    aws events put-targets \
        --rule "${EVENTBRIDGE_RULE_NAME}" \
        --targets "Id=1,Arn=${S3TABLES_IMPORT_LAMBDA_ARN}" \
        --region ${AWS_REGION}

    print_success "EventBridge target configured"

    export EVENTBRIDGE_RULE_ARN="arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/${EVENTBRIDGE_RULE_NAME}"

    save_orchestration_config
    print_success "Step 12 Complete: Event-driven pipeline configured"
}

# ============================================================================
# Step 13: Verify ClinVar Data Availability
# ============================================================================

load_clinvar_data() {
    print_step "13" "Verifying ClinVar Data Availability"

    print_info "ClinVar data is used by VEP workflow for variant annotation"
    print_info "Checking ClinVar data in S3..."

    # Check if ClinVar data exists in S3
    CLINVAR_S3_PATH="s3://${CLINVAR_BUCKET}/clinvar/clinvar_20260315.vcf.gz"

    if aws s3 ls "${CLINVAR_S3_PATH}" &> /dev/null; then
        print_success "ClinVar data found: ${CLINVAR_S3_PATH}"

        # Get file size
        FILE_SIZE=$(aws s3 ls "${CLINVAR_S3_PATH}" | awk '{print $3}')
        FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
        print_info "File size: ${FILE_SIZE_MB} MB"

        print_info "ClinVar data is available for VEP annotation workflow"
        print_success "Step 13 Complete: ClinVar data verified"
    else
        print_error "ClinVar data not found at: ${CLINVAR_S3_PATH}"
        print_warning "Run deploy-unified.sh step 3 to download and upload ClinVar data"
        return 1
    fi

    # Optional: Load ClinVar as a separate sample if needed
    print_info ""
    print_info "Note: ClinVar annotations are applied during VEP workflow execution"
    print_info "If you need ClinVar as a queryable dataset, you can load it using:"
    print_info "  python3 load_vcf_schema3.py ${CLINVAR_S3_PATH} --sample clinvar --bucket-arn ${TABLE_BUCKET_ARN}"
}

# ============================================================================
# Step 14: Validate Pipeline
# ============================================================================

validate_pipeline() {
    print_step "14" "Validating Pipeline Configuration"

    print_info "Checking AWS Batch resources..."

    # Check compute environment
    COMPUTE_ENV_STATUS=$(aws batch describe-compute-environments \
        --compute-environments "${BATCH_COMPUTE_ENV_NAME}" \
        --region ${AWS_REGION} \
        --query 'computeEnvironments[0].status' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [ "${COMPUTE_ENV_STATUS}" = "VALID" ]; then
        print_success "Compute environment: ${COMPUTE_ENV_STATUS}"
    else
        print_error "Compute environment: ${COMPUTE_ENV_STATUS}"
    fi

    # Check job queue
    JOB_QUEUE_STATUS=$(aws batch describe-job-queues \
        --job-queues "${BATCH_JOB_QUEUE_NAME}" \
        --region ${AWS_REGION} \
        --query 'jobQueues[0].status' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [ "${JOB_QUEUE_STATUS}" = "VALID" ]; then
        print_success "Job queue: ${JOB_QUEUE_STATUS}"
    else
        print_error "Job queue: ${JOB_QUEUE_STATUS}"
    fi

    print_info "Checking Lambda functions..."

    # Check workflow trigger Lambda
    WORKFLOW_LAMBDA_STATUS=$(aws lambda get-function \
        --function-name "${STACK_NAME}-workflow-trigger" \
        --region ${AWS_REGION} \
        --query 'Configuration.State' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [ "${WORKFLOW_LAMBDA_STATUS}" = "Active" ]; then
        print_success "Workflow trigger Lambda: ${WORKFLOW_LAMBDA_STATUS}"
    else
        print_error "Workflow trigger Lambda: ${WORKFLOW_LAMBDA_STATUS}"
    fi

    # Check S3 Tables import Lambda
    S3TABLES_LAMBDA_STATUS=$(aws lambda get-function \
        --function-name "${STACK_NAME}-s3tables-import" \
        --region ${AWS_REGION} \
        --query 'Configuration.State' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [ "${S3TABLES_LAMBDA_STATUS}" = "Active" ]; then
        print_success "S3 Tables import Lambda: ${S3TABLES_LAMBDA_STATUS}"
    else
        print_error "S3 Tables import Lambda: ${S3TABLES_LAMBDA_STATUS}"
    fi

    print_info "Checking EventBridge rule..."

    # Check EventBridge rule
    EVENTBRIDGE_STATUS=$(aws events describe-rule \
        --name "${STACK_NAME}-workflow-completion" \
        --region ${AWS_REGION} \
        --query 'State' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [ "${EVENTBRIDGE_STATUS}" = "ENABLED" ]; then
        print_success "EventBridge rule: ${EVENTBRIDGE_STATUS}"
    else
        print_error "EventBridge rule: ${EVENTBRIDGE_STATUS}"
    fi

    print_info "Checking S3 event notification..."

    # Check S3 notification
    S3_NOTIFICATION=$(aws s3api get-bucket-notification-configuration \
        --bucket "${VCF_INPUT_BUCKET}" \
        --query 'LambdaFunctionConfigurations[0].Id' \
        --output text 2>/dev/null || echo "NOT_CONFIGURED")

    if [ "${S3_NOTIFICATION}" != "NOT_CONFIGURED" ]; then
        print_success "S3 event notification: Configured"
    else
        print_error "S3 event notification: ${S3_NOTIFICATION}"
    fi

    print_success "Step 14 Complete: Pipeline validation finished"
}

# ============================================================================
# Main Menu and Execution
# ============================================================================

show_menu() {
    print_header "Pipeline Orchestration Deployment"

    echo "Select deployment step:"
    echo ""
    echo "${CYAN}Orchestration Steps:${NC}"
    echo "  ${GREEN}10)${NC} Create AWS Batch Infrastructure"
    echo "  ${GREEN}11)${NC} Create Lambda Functions"
    echo "  ${GREEN}12)${NC} Configure Event-Driven Pipeline"
    echo "  ${GREEN}13)${NC} Load ClinVar Data to S3 Tables"
    echo "  ${GREEN}14)${NC} Validate Pipeline Configuration"
    echo ""
    echo "${CYAN}Quick Options:${NC}"
    echo "  ${YELLOW}a)${NC} Run All Orchestration Steps (10-14)"
    echo "  ${YELLOW}s)${NC} Show Pipeline Status"
    echo ""
    echo "  ${RED}0)${NC} Exit"
    echo ""
}

run_all_orchestration() {
    print_header "Running All Orchestration Steps (10-14)"

    create_batch_infrastructure
    create_lambda_functions
    configure_event_pipeline
    load_clinvar_data
    validate_pipeline

    print_header "Orchestration Deployment Complete!"
    print_success "Event-driven pipeline is ready"
    print_info ""
    print_info "Pipeline Flow:"
    print_info "  1. Upload VCF to s3://${VCF_INPUT_BUCKET}/"
    print_info "  2. Lambda triggers HealthOmics workflow"
    print_info "  3. Workflow completion triggers S3 Tables import"
    print_info "  4. Batch job loads results to S3 Tables"
    print_info "  5. Query with Athena or deploy Bedrock Agent"
    print_info ""
    print_info "Next Steps:"
    print_info "  • Test pipeline: aws s3 cp test.vcf.gz s3://${VCF_INPUT_BUCKET}/"
    print_info "  • Deploy agent: ./deploy-agent.sh"
    print_info "  • Monitor: aws dynamodb scan --table-name ${DYNAMODB_TABLE}"
}

show_status() {
    print_header "Pipeline Orchestration Status"

    load_orchestration_config

    echo -e "${BLUE}AWS Batch Resources:${NC}"
    [ -n "${BATCH_COMPUTE_ENV_NAME}" ] && echo -e "  Compute Env: ${GREEN}${BATCH_COMPUTE_ENV_NAME}${NC}" || echo -e "  Compute Env: ${RED}NOT SET${NC}"
    [ -n "${BATCH_JOB_QUEUE_NAME}" ] && echo -e "  Job Queue: ${GREEN}${BATCH_JOB_QUEUE_NAME}${NC}" || echo -e "  Job Queue: ${RED}NOT SET${NC}"
    [ -n "${BATCH_JOB_DEFINITION_NAME}" ] && echo -e "  Job Definition: ${GREEN}${BATCH_JOB_DEFINITION_NAME}${NC}" || echo -e "  Job Definition: ${RED}NOT SET${NC}"

    echo -e "\n${BLUE}Lambda Functions:${NC}"
    [ -n "${WORKFLOW_TRIGGER_LAMBDA_ARN}" ] && echo -e "  Workflow Trigger: ${GREEN}Created${NC}" || echo -e "  Workflow Trigger: ${RED}NOT SET${NC}"
    [ -n "${S3TABLES_IMPORT_LAMBDA_ARN}" ] && echo -e "  S3 Tables Import: ${GREEN}Created${NC}" || echo -e "  S3 Tables Import: ${RED}NOT SET${NC}"

    echo -e "\n${BLUE}Event Configuration:${NC}"
    [ -n "${EVENTBRIDGE_RULE_ARN}" ] && echo -e "  EventBridge: ${GREEN}Configured${NC}" || echo -e "  EventBridge: ${RED}NOT SET${NC}"
}

main() {
    check_prerequisites
    load_orchestration_config

    if [ $# -eq 0 ]; then
        # Interactive mode
        while true; do
            show_menu
            read -p "Enter your choice: " choice

            case $choice in
                10) create_batch_infrastructure ;;
                11) create_lambda_functions ;;
                12) configure_event_pipeline ;;
                13) load_clinvar_data ;;
                14) validate_pipeline ;;
                a|A) run_all_orchestration ;;
                s|S) show_status ;;
                0) print_info "Exiting..."; exit 0 ;;
                *) print_error "Invalid choice" ;;
            esac

            echo ""
            read -p "Press Enter to continue..."
        done
    else
        # Command-line mode
        case $1 in
            all) run_all_orchestration ;;
            batch) create_batch_infrastructure ;;
            lambda) create_lambda_functions ;;
            events) configure_event_pipeline ;;
            clinvar) load_clinvar_data ;;
            validate) validate_pipeline ;;
            status) show_status ;;
            *)
                echo "Usage: $0 [all|batch|lambda|events|clinvar|validate|status]"
                echo "  all      - Run all orchestration steps (10-14)"
                echo "  batch    - Create AWS Batch infrastructure"
                echo "  lambda   - Create Lambda functions"
                echo "  events   - Configure event-driven pipeline"
                echo "  clinvar  - Load ClinVar data to S3 Tables"
                echo "  validate - Validate pipeline configuration"
                echo "  status   - Show pipeline status"
                exit 1
                ;;
        esac
    fi
}

# Run main
main "$@"
