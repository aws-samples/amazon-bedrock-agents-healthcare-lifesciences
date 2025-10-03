# VCF Processing and Genomic Analysis System - Setup Checklist

## 📋 Pre-Setup Requirements

### ✅ AWS Account Setup
- [ ] AWS Account with administrative permissions
- [ ] AWS CLI installed and configured
- [ ] Python 3.9+ environment
- [ ] Jupyter Notebook environment
- [ ] boto3 version 1.37.1 or higher

### ✅ AWS Service Access
Ensure your AWS account has access to:
- [ ] AWS HealthOmics
- [ ] Amazon DynamoDB
- [ ] AWS Lambda
- [ ] Amazon S3
- [ ] Amazon Athena
- [ ] AWS Glue
- [ ] AWS Lake Formation
- [ ] Amazon Bedrock
- [ ] Amazon EventBridge

## 🏗️ Infrastructure Setup (Prerequisites_creation.ipynb)

### ✅ Step 1: Initial Configuration
- [ ] Update AWS profile in notebook: `os.environ['AWS_PROFILE'] = 'your-profile'`
- [ ] Verify AWS credentials and region
- [ ] Install/upgrade required packages (boto3, botocore, awscli)

### ✅ Step 2: DynamoDB Table Creation
- [ ] Create `VcfImportTracking3` table
- [ ] Verify table has `SampleID` as primary key
- [ ] Confirm billing mode is `PAY_PER_REQUEST`

### ✅ Step 3: IAM Role and Policies
- [ ] Create `VcfProcessorLambdaRole3` IAM role
- [ ] Attach comprehensive policy with permissions for:
  - [ ] CloudWatch Logs (create/write)
  - [ ] S3 (read/write objects, list buckets)
  - [ ] DynamoDB (put/update/get/scan items)
  - [ ] HealthOmics (start/get import jobs, manage stores)
  - [ ] Lake Formation (grant/revoke permissions)
  - [ ] Glue (manage tables and databases)
  - [ ] KMS (decrypt/encrypt operations)
- [ ] **IMPORTANT**: Update KMS key ARN in policy with your actual key

### ✅ Step 4: HealthOmics Resources
- [ ] Create or verify reference store exists
- [ ] Import reference genome (if needed)
- [ ] Create variant store with analytics enabled
- [ ] Note variant store name and ID for Lambda configuration
- [ ] **CRITICAL**: Enable analytics on variant store for Athena queries

### ✅ Step 5: Lambda Function Deployment
- [ ] Deploy `VcfProcessor3` Lambda function using `lambda_function_fixed_final.py`
- [ ] Set environment variables:
  - [ ] `VARIANT_STORE_NAME`: Your variant store name
  - [ ] `VARIANT_STORE_ID`: Your variant store ID
  - [ ] `DYNAMODB_TABLE`: `VcfImportTracking3`
- [ ] Set timeout to 900 seconds (15 minutes)
- [ ] Verify function has correct IAM role attached

### ✅ Step 6: S3 Event Configuration
- [ ] **UPDATE**: Configure S3 URI in notebook (currently: `s3://YOUR_S3_BUCKET/YOUR_PREFIX/`)
- [ ] Set up S3 event notifications for `.hard-filtered.vcf.gz` files
- [ ] Grant S3 permission to invoke Lambda function
- [ ] Test S3 trigger by uploading a sample VCF file

### ✅ Step 7: Lake Formation Setup
- [ ] Create `vcf_analysis_db` database in Glue
- [ ] Create resource links to HealthOmics tables
- [ ] Grant necessary Lake Formation permissions
- [ ] Verify Athena can query the tables

### ✅ Step 8: Athena Configuration
- [ ] Verify Athena workgroup uses Engine Version 3
- [ ] Test basic queries against variant store tables
- [ ] Confirm data is accessible through Athena

## 🤖 Agent Setup (advanced-vcf-interpreter-strands-agents.ipynb)

### ✅ Step 1: Dependencies Installation
- [ ] Install Strands agents: `pip install strands-agents strands-agents-tools`
- [ ] Verify boto3 version ≥ 1.37.1
- [ ] Import required libraries and functions

### ✅ Step 2: AWS Configuration
- [ ] Verify AWS region and account ID detection
- [ ] Initialize AWS clients (DynamoDB, Athena, Bedrock, Glue, RAM)
- [ ] Test client connectivity

### ✅ Step 3: Agent Configuration
- [ ] Configure Bedrock model (default: Claude 3.5 Sonnet)
- [ ] Set up agent instructions and system prompts
- [ ] Define genomic analysis tools
- [ ] Configure database and table references

### ✅ Step 4: Agent Testing
- [ ] Initialize Strands agent
- [ ] Test basic queries: "List available patients"
- [ ] Verify agent can access genomic data
- [ ] Test complex analysis queries

## 🧪 Testing and Verification

### ✅ Infrastructure Testing
- [ ] Upload test VCF file to S3 bucket
- [ ] Verify Lambda function triggers automatically
- [ ] Check DynamoDB for job tracking records
- [ ] Monitor CloudWatch logs for errors
- [ ] Confirm job progresses: SUBMITTED → IN_PROGRESS → COMPLETED

### ✅ Data Access Testing
- [ ] Query data through Athena workbench
- [ ] Test resource links in Lake Formation
- [ ] Verify agent can execute genomic queries
- [ ] Test various analysis scenarios

### ✅ Agent Functionality Testing
- [ ] Patient listing queries
- [ ] Variant significance analysis
- [ ] Gene-based searches
- [ ] Clinical interpretation queries
- [ ] Comparative analysis between patients

## 🔧 Configuration Updates Required

**📋 IMPORTANT**: See `CONFIGURATION_PLACEHOLDERS.md` for a complete reference of all placeholders that need to be replaced with your actual AWS values.

### ✅ Critical Updates Needed
1. **S3 Bucket URI**: Update in Prerequisites notebook
   ```python
   s3_uri = "s3://your-bucket/your-prefix/"  # UPDATE THIS
   ```

2. **KMS Key ARN**: Update in IAM policy
   ```json
   "Resource": "arn:aws:kms:<YOUR_REGION>:<YOUR_ACCOUNT_ID>:key/<YOUR_KMS_KEY_ID>"
   ```

3. **Reference ARN**: Update with your reference genome
   ```python
   reference_arn = 'arn:aws:omics:<YOUR_REGION>:<YOUR_ACCOUNT_ID>:referenceStore/YOUR_REF_STORE_ID/reference/YOUR_REFERENCE_ID'
   ```

4. **AWS Profile**: Update in both notebooks
   ```python
   os.environ['AWS_PROFILE'] = 'your-aws-profile'
   ```

## 🚨 Common Setup Issues

### ✅ Lambda Function Issues
- [ ] **Timeout errors**: Increase timeout to 900 seconds
- [ ] **Permission errors**: Verify IAM role has all required permissions
- [ ] **Environment variables**: Ensure all variables are set correctly
- [ ] **S3 triggers**: Verify S3 event notifications are configured

### ✅ Athena Query Issues
- [ ] **Table not found**: Verify resource links are created
- [ ] **Permission denied**: Check Lake Formation permissions
- [ ] **Engine version**: Ensure workgroup uses Athena Engine Version 3
- [ ] **Analytics disabled**: Verify variant store has analytics enabled

### ✅ Agent Connection Issues
- [ ] **AWS credentials**: Verify credentials are properly configured
- [ ] **Bedrock access**: Ensure Bedrock model permissions
- [ ] **Region mismatch**: Verify all services use same region
- [ ] **Network connectivity**: Check VPC/security group settings

## 📊 Monitoring and Maintenance

### ✅ Regular Checks
- [ ] Monitor CloudWatch logs for Lambda function
- [ ] Check DynamoDB table for job status updates
- [ ] Verify S3 event notifications are working
- [ ] Monitor AWS costs for HealthOmics usage
- [ ] Review Athena query performance

### ✅ Troubleshooting Commands
```bash
# Check DynamoDB records
aws dynamodb scan --table-name VcfImportTracking3 --output table

# Test Lambda function
aws lambda invoke --function-name VcfProcessor3 --payload '{"check_status": true}' response.json

# Verify S3 notifications
aws s3api get-bucket-notification-configuration --bucket YOUR_S3_BUCKET_NAME

# Check Athena workgroups
aws athena list-work-groups

# Test Bedrock access
aws bedrock list-foundation-models --region <YOUR_REGION>
```

## 🔒 Security Checklist

### ✅ Data Protection
- [ ] S3 bucket encryption enabled
- [ ] VCF files have appropriate access controls
- [ ] DynamoDB encryption at rest enabled
- [ ] CloudWatch logs retention configured

### ✅ Access Control
- [ ] IAM roles follow least privilege principle
- [ ] Lake Formation permissions properly configured
- [ ] Bedrock model access restricted to authorized users
- [ ] S3 bucket policies restrict access

### ✅ Compliance
- [ ] HIPAA compliance considerations (if applicable)
- [ ] Data retention policies implemented
- [ ] Audit logging enabled
- [ ] Access monitoring configured

## ✅ Final Verification

### ✅ End-to-End Test
1. [ ] Upload VCF file to S3
2. [ ] Verify automatic processing starts
3. [ ] Check job completes successfully
4. [ ] Query data through agent
5. [ ] Perform genomic analysis
6. [ ] Verify results are accurate

### ✅ Documentation
- [ ] Update configuration values in notebooks
- [ ] Document any custom modifications
- [ ] Create user guide for team members
- [ ] Set up monitoring alerts

---

**Setup Complete**: When all items are checked, your VCF processing and genomic analysis system is ready for production use.

**Estimated Setup Time**: 2-4 hours (depending on data size and AWS service provisioning)

**Next Steps**: Begin uploading VCF files and using the genomic analysis agent for research and clinical workflows.
