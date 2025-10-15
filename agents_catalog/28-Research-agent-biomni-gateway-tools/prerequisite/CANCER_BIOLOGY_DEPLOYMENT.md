# Cancer Biology Gateway Deployment Guide

This guide provides step-by-step instructions for deploying the Cancer Biology Gateway integration to the AgentCore Gateway infrastructure.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Steps](#deployment-steps)
  - [Step 1: Package Lambda Function](#step-1-package-lambda-function)
  - [Step 2: Upload to S3](#step-2-upload-to-s3)
  - [Step 3: Deploy CloudFormation Stack](#step-3-deploy-cloudformation-stack)
  - [Step 4: Create Gateway Target](#step-4-create-gateway-target)
  - [Step 5: Verify Deployment](#step-5-verify-deployment)
  - [Step 6: Test Cancer Biology Functions](#step-6-test-cancer-biology-functions)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)

---

## Prerequisites

Before deploying the Cancer Biology Gateway, ensure you have the following:

### Infrastructure Requirements

1. **Existing AgentCore Gateway Infrastructure**
   - Gateway must be deployed and operational
   - Gateway ID stored in SSM parameter: `/app/researchapp/agentcore/gateway_id`
   - Gateway IAM role configured with Lambda invocation permissions

2. **AWS Resources**
   - S3 bucket for Lambda deployment packages
   - IAM permissions to create Lambda functions, IAM roles, and SSM parameters
   - CloudFormation stack deployment permissions

3. **AWS Credentials**
   - AWS CLI configured with appropriate credentials
   - Permissions for:
     - Lambda (CreateFunction, UpdateFunctionCode, CreateLayer)
     - IAM (CreateRole, AttachRolePolicy)
     - SSM (PutParameter, GetParameter)
     - S3 (PutObject, GetObject)
     - CloudFormation (CreateStack, UpdateStack)
     - Bedrock AgentCore (CreateGatewayTarget, ListGatewayTargets)

### Software Requirements

1. **Python 3.12**
   - Required for Lambda runtime compatibility
   - Verify: `python3 --version`

2. **AWS CLI**
   - Version 2.x or later
   - Verify: `aws --version`

3. **Required Python Packages**
   - boto3
   - click
   - All dependencies will be packaged automatically

### File Requirements

Ensure the following files exist in your workspace:

```
agents_catalog/28-Research-agent-biomni-gateway-tools/
├── prerequisite/
│   ├── cancer_biology.py                          # Cancer biology implementation
│   ├── create_cancer_biology_lambda_zip.py        # Packaging script
│   ├── infrastructure.yaml                        # CloudFormation template
│   └── lambda/
│       ├── cancer_biology_api_spec.json           # API specification
│       └── python/
│           └── cancer_biology_lambda_function.py  # Lambda handler
└── scripts/
    ├── create_cancer_biology_target.py            # Target creation script
    └── utils.py                                   # Utility functions
```

---

## Deployment Steps

### Step 1: Package Lambda Function

The Cancer Biology Lambda function is deployed using two separate packages to stay within AWS Lambda size limits:
- **Lambda Layer**: Contains Python dependencies (pandas, numpy, scipy, etc.)
- **Lambda Function**: Contains only the code (handler and cancer_biology.py)

#### 1.1 Navigate to the prerequisite directory

```bash
cd agents_catalog/28-Research-agent-biomni-gateway-tools/prerequisite
```

#### 1.2 Run the packaging script

```bash
python3 create_cancer_biology_lambda_zip.py
```

#### 1.3 Verify package creation

The script will create two ZIP files:

```bash
ls -lh *.zip
```

Expected output:
```
cancer-biology-lambda-layer.zip      # Lambda Layer with dependencies (~50-150 MB)
cancer-biology-lambda-function.zip   # Lambda Function with code only (~1-5 MB)
```

#### 1.4 Review packaging output

The script provides detailed information about:
- Installed dependencies
- Package optimization (removed files)
- Compressed and uncompressed sizes
- Warnings if size limits are exceeded

**Important Notes:**
- The Lambda Layer uncompressed size must be under 250 MB
- If you see a size warning, you may need to optimize dependencies
- The packaging script automatically removes unnecessary files (tests, docs, etc.)

---

### Step 2: Upload to S3

Upload both ZIP files to your S3 bucket for Lambda deployment.

#### 2.1 Set environment variables

```bash
export S3_BUCKET="your-lambda-deployment-bucket"
export S3_PREFIX="cancer-biology-gateway"  # Optional prefix
```

#### 2.2 Upload Lambda Layer

```bash
aws s3 cp cancer-biology-lambda-layer.zip \
  s3://${S3_BUCKET}/${S3_PREFIX}/cancer-biology-lambda-layer.zip
```

#### 2.3 Upload Lambda Function

```bash
aws s3 cp cancer-biology-lambda-function.zip \
  s3://${S3_BUCKET}/${S3_PREFIX}/cancer-biology-lambda-function.zip
```

#### 2.4 Verify uploads

```bash
aws s3 ls s3://${S3_BUCKET}/${S3_PREFIX}/
```

Expected output:
```
2025-01-15 10:30:00   52428800 cancer-biology-lambda-layer.zip
2025-01-15 10:30:05    1048576 cancer-biology-lambda-function.zip
```

---

### Step 3: Deploy CloudFormation Stack

Deploy or update the CloudFormation stack to create the Cancer Biology Lambda function and associated resources.

#### 3.1 Set CloudFormation parameters

```bash
export STACK_NAME="research-app-infrastructure"
export AWS_REGION="us-east-1"  # Your AWS region
```

#### 3.2 Deploy the stack

If this is a new stack:

```bash
aws cloudformation create-stack \
  --stack-name ${STACK_NAME} \
  --template-body file://infrastructure.yaml \
  --parameters \
    ParameterKey=S3BucketName,ParameterValue=${S3_BUCKET} \
    ParameterKey=S3KeyPrefix,ParameterValue=${S3_PREFIX} \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}
```

If updating an existing stack:

```bash
aws cloudformation update-stack \
  --stack-name ${STACK_NAME} \
  --template-body file://infrastructure.yaml \
  --parameters \
    ParameterKey=S3BucketName,ParameterValue=${S3_BUCKET} \
    ParameterKey=S3KeyPrefix,ParameterValue=${S3_PREFIX} \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}
```

#### 3.3 Monitor stack deployment

```bash
aws cloudformation wait stack-create-complete \
  --stack-name ${STACK_NAME} \
  --region ${AWS_REGION}
```

Or for updates:

```bash
aws cloudformation wait stack-update-complete \
  --stack-name ${STACK_NAME} \
  --region ${AWS_REGION}
```

#### 3.4 Verify stack resources

```bash
aws cloudformation describe-stack-resources \
  --stack-name ${STACK_NAME} \
  --region ${AWS_REGION} \
  | grep -A 5 "CancerBiology"
```

Expected resources:
- `CancerBiologyLambdaLayer` - Lambda Layer with dependencies
- `CancerBiologyLambda` - Lambda function
- `CancerBiologyLambdaRole` - IAM execution role
- `CancerBiologyLambdaArnParameter` - SSM parameter with Lambda ARN

---

### Step 4: Create Gateway Target

Create the gateway target that connects the AgentCore Gateway to the Cancer Biology Lambda function.

#### 4.1 Navigate to scripts directory

```bash
cd ../scripts
```

#### 4.2 Run the target creation script

```bash
python3 create_cancer_biology_target.py create
```

The script will:
1. Read the gateway ID from SSM parameter
2. Load the cancer biology API specification
3. Retrieve the Cancer Biology Lambda ARN from SSM
4. Create the gateway target with MCP protocol configuration
5. Store the target ID in SSM parameter

#### 4.3 Review creation output

Expected output:
```
🚀 Creating cancer biology gateway target
📍 Region: us-east-1
📖 Using gateway ID from SSM: gtw-abc123xyz
📄 Loaded API spec with 6 tools
🔧 Cancer biology tools:
   - analyze_ddr_network_in_cancer
   - analyze_cell_senescence_and_apoptosis
   - detect_and_annotate_somatic_mutations
   - detect_and_characterize_structural_variations
   - perform_gene_expression_nmf_analysis
   - analyze_copy_number_purity_ploidy_and_focal_events
Creating cancer biology target for gateway: gtw-abc123xyz
Lambda ARN: arn:aws:lambda:us-east-1:123456789012:function:CancerBiologyLambda
Number of tools: 6
✅ Cancer biology target created: tgt-def456uvw
✅ Target ID saved to SSM parameter
🎉 Cancer biology target created successfully with ID: tgt-def456uvw
```

#### 4.4 Verify SSM parameters

```bash
aws ssm get-parameter \
  --name "/app/researchapp/agentcore/cancer_biology_target_id" \
  --region ${AWS_REGION}
```

---

### Step 5: Verify Deployment

Verify that the Cancer Biology Gateway is properly deployed and accessible.

#### 5.1 List gateway targets

```bash
aws bedrock-agentcore-control list-gateway-targets \
  --gateway-identifier $(aws ssm get-parameter \
    --name "/app/researchapp/agentcore/gateway_id" \
    --query "Parameter.Value" \
    --output text) \
  --region ${AWS_REGION}
```

Expected output should include:
```json
{
  "targetSummaries": [
    {
      "targetId": "tgt-def456uvw",
      "name": "CancerBiologyTarget",
      "description": "Cancer Biology Analysis Tools - DDR network, cell senescence/apoptosis, somatic mutations, structural variations, NMF analysis, and CNV analysis",
      "status": "AVAILABLE"
    }
  ]
}
```

#### 5.2 Verify Lambda function

```bash
aws lambda get-function \
  --function-name CancerBiologyLambda \
  --region ${AWS_REGION}
```

Check:
- Runtime: `python3.12`
- Handler: `cancer_biology_lambda_function.lambda_handler`
- Memory: `3008 MB`
- Timeout: `900 seconds`
- Layers: Should include the Cancer Biology Lambda Layer

#### 5.3 Check Lambda logs

```bash
aws logs tail /aws/lambda/CancerBiologyLambda \
  --follow \
  --region ${AWS_REGION}
```

---

### Step 6: Test Cancer Biology Functions

Test each cancer biology function through the gateway to ensure proper integration.

#### 6.1 Prepare test data

Create sample test files or use existing datasets:

```bash
# Example: Create a small test expression data file
cat > /tmp/test_expression.csv << EOF
gene_id,sample1,sample2,sample3
BRCA1,5.2,6.1,4.8
TP53,7.3,8.2,6.9
ATM,4.1,5.0,3.8
EOF
```

Upload test data to S3 if needed:

```bash
aws s3 cp /tmp/test_expression.csv s3://${S3_BUCKET}/test-data/
```

#### 6.2 Test via AgentCore Runtime

Create a test script to invoke functions through the gateway:

```python
# test_cancer_biology.py
import boto3
import json

# Initialize AgentCore Runtime client
runtime_client = boto3.client('bedrock-agentcore-runtime', region_name='us-east-1')

# Get gateway ID
ssm_client = boto3.client('ssm', region_name='us-east-1')
gateway_id = ssm_client.get_parameter(
    Name='/app/researchapp/agentcore/gateway_id'
)['Parameter']['Value']

# Test analyze_ddr_network_in_cancer
response = runtime_client.invoke_gateway_tool(
    gatewayIdentifier=gateway_id,
    toolName='analyze_ddr_network_in_cancer',
    parameters={
        'expression_data_path': 's3://your-bucket/test-data/test_expression.csv',
        'mutation_data_path': 's3://your-bucket/test-data/test_mutations.csv',
        'output_dir': '/tmp/ddr_results'
    }
)

print("DDR Network Analysis Result:")
print(response['body'])
```

Run the test:

```bash
python3 test_cancer_biology.py
```

#### 6.3 Test each function

Test all 6 cancer biology functions:

1. **analyze_ddr_network_in_cancer**
   ```python
   parameters = {
       'expression_data_path': 's3://bucket/expression.csv',
       'mutation_data_path': 's3://bucket/mutations.csv',
       'output_dir': '/tmp/results'
   }
   ```

2. **analyze_cell_senescence_and_apoptosis**
   ```python
   parameters = {
       'fcs_file_path': 's3://bucket/flow_cytometry.fcs'
   }
   ```

3. **detect_and_annotate_somatic_mutations**
   ```python
   parameters = {
       'tumor_bam': 's3://bucket/tumor.bam',
       'normal_bam': 's3://bucket/normal.bam',
       'reference_genome': 's3://bucket/reference.fa',
       'output_prefix': 'mutations'
   }
   ```

4. **detect_and_characterize_structural_variations**
   ```python
   parameters = {
       'bam_file_path': 's3://bucket/sample.bam',
       'reference_genome_path': 's3://bucket/reference.fa',
       'output_dir': '/tmp/sv_results'
   }
   ```

5. **perform_gene_expression_nmf_analysis**
   ```python
   parameters = {
       'expression_data_path': 's3://bucket/expression.csv',
       'n_components': 10,
       'normalize': True
   }
   ```

6. **analyze_copy_number_purity_ploidy_and_focal_events**
   ```python
   parameters = {
       'tumor_bam': 's3://bucket/tumor.bam',
       'reference_genome': 's3://bucket/reference.fa',
       'output_dir': '/tmp/cnv_results'
   }
   ```

#### 6.4 Verify research logs

Each function should return a detailed research log containing:
- Analysis parameters
- Processing steps
- Results summary
- Output file locations
- Execution timestamp

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Lambda Package Too Large

**Symptom:**
```
Error: Uncompressed size exceeds 250 MB Lambda limit
```

**Solution:**
1. Review installed dependencies and remove unnecessary packages
2. Use Lambda Layers for large dependencies
3. Optimize package by removing test files, documentation, and examples
4. Consider using AWS Lambda Container Images for very large packages

```bash
# Check package contents
unzip -l cancer-biology-lambda-layer.zip | head -20

# Remove specific packages if not needed
# Edit create_cancer_biology_lambda_zip.py to exclude packages
```

#### Issue 2: Gateway Target Creation Fails

**Symptom:**
```
❌ Error creating cancer biology target: Gateway not found
```

**Solution:**
1. Verify gateway exists and is in AVAILABLE state:
   ```bash
   aws bedrock-agentcore-control get-gateway \
     --gateway-identifier $(aws ssm get-parameter \
       --name "/app/researchapp/agentcore/gateway_id" \
       --query "Parameter.Value" \
       --output text)
   ```

2. Check SSM parameters are set correctly:
   ```bash
   aws ssm get-parameters \
     --names \
       "/app/researchapp/agentcore/gateway_id" \
       "/app/researchapp/agentcore/cancer_biology_lambda_arn"
   ```

3. Verify IAM permissions for bedrock-agentcore-control:CreateGatewayTarget

#### Issue 3: Lambda Function Timeout

**Symptom:**
```
Task timed out after 900.00 seconds
```

**Solution:**
1. Increase Lambda timeout in CloudFormation template (max 900 seconds)
2. Optimize cancer biology functions for performance
3. Use smaller test datasets
4. Consider asynchronous processing for long-running analyses

```yaml
# In infrastructure.yaml
CancerBiologyLambda:
  Properties:
    Timeout: 900  # Maximum allowed
```

#### Issue 4: Missing Dependencies in Lambda

**Symptom:**
```
ModuleNotFoundError: No module named 'pandas'
```

**Solution:**
1. Verify Lambda Layer is attached to the function:
   ```bash
   aws lambda get-function-configuration \
     --function-name CancerBiologyLambda \
     --query "Layers"
   ```

2. Recreate the Lambda Layer with all dependencies:
   ```bash
   python3 create_cancer_biology_lambda_zip.py
   # Re-upload and update CloudFormation stack
   ```

3. Check Lambda Layer size limits (250 MB uncompressed)

#### Issue 5: Permission Denied Errors

**Symptom:**
```
AccessDeniedException: User is not authorized to perform: lambda:InvokeFunction
```

**Solution:**
1. Update Gateway IAM role to allow Lambda invocation:
   ```json
   {
     "Effect": "Allow",
     "Action": "lambda:InvokeFunction",
     "Resource": "arn:aws:lambda:*:*:function:CancerBiologyLambda"
   }
   ```

2. Verify Lambda execution role has S3 permissions for data access:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "s3:GetObject",
       "s3:PutObject"
     ],
     "Resource": "arn:aws:s3:::your-bucket/*"
   }
   ```

#### Issue 6: API Specification Not Found

**Symptom:**
```
❌ API specification file not found: prerequisite/lambda/cancer_biology_api_spec.json
```

**Solution:**
1. Verify the API spec file exists:
   ```bash
   ls -l prerequisite/lambda/cancer_biology_api_spec.json
   ```

2. If missing, regenerate from cancer_biology.py metadata
3. Ensure you're running the script from the correct directory

#### Issue 7: Tool Name Not Recognized

**Symptom:**
```
Unknown tool: analyze_ddr_network_in_cancer
```

**Solution:**
1. Check tool name spelling and case sensitivity
2. Verify API specification includes all 6 tools
3. Check Lambda logs for tool name extraction:
   ```bash
   aws logs tail /aws/lambda/CancerBiologyLambda --follow
   ```

4. Verify prefix stripping logic in Lambda handler

#### Issue 8: S3 Access Denied

**Symptom:**
```
botocore.exceptions.ClientError: An error occurred (403) when calling the GetObject operation: Forbidden
```

**Solution:**
1. Add S3 permissions to Lambda execution role
2. Verify S3 bucket policy allows Lambda access
3. Check S3 object ACLs
4. Ensure bucket and Lambda are in the same region (or enable cross-region access)

---

## Cleanup

To remove the Cancer Biology Gateway integration:

### 1. Delete Gateway Target

```bash
cd agents_catalog/28-Research-agent-biomni-gateway-tools/scripts
python3 create_cancer_biology_target.py delete --confirm
```

### 2. Delete Lambda Function and Layer

```bash
# Delete Lambda function
aws lambda delete-function \
  --function-name CancerBiologyLambda \
  --region ${AWS_REGION}

# Delete Lambda Layer (get version from describe-function output)
aws lambda delete-layer-version \
  --layer-name CancerBiologyLambdaLayer \
  --version-number 1 \
  --region ${AWS_REGION}
```

### 3. Delete SSM Parameters

```bash
aws ssm delete-parameter \
  --name "/app/researchapp/agentcore/cancer_biology_lambda_arn" \
  --region ${AWS_REGION}

aws ssm delete-parameter \
  --name "/app/researchapp/agentcore/cancer_biology_target_id" \
  --region ${AWS_REGION}
```

### 4. Delete S3 Objects

```bash
aws s3 rm s3://${S3_BUCKET}/${S3_PREFIX}/cancer-biology-lambda-layer.zip
aws s3 rm s3://${S3_BUCKET}/${S3_PREFIX}/cancer-biology-lambda-function.zip
```

### 5. Delete CloudFormation Stack (if dedicated)

```bash
aws cloudformation delete-stack \
  --stack-name ${STACK_NAME} \
  --region ${AWS_REGION}

aws cloudformation wait stack-delete-complete \
  --stack-name ${STACK_NAME} \
  --region ${AWS_REGION}
```

---

## Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [CloudFormation Best Practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)
- [Lambda Layer Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)

---

## Support

For issues or questions:
1. Check CloudWatch Logs for Lambda execution details
2. Review CloudFormation stack events for deployment issues
3. Verify all prerequisites are met
4. Consult the troubleshooting section above
5. Contact your AWS support team for infrastructure issues

---

**Last Updated:** 2025-01-15
**Version:** 1.0.0
