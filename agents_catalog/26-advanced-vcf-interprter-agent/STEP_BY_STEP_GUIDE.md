# Step-by-Step Implementation Guide

This guide provides detailed instructions for implementing the VCF Processing and Genomic Analysis System in a new AWS account from scratch.

## 🎯 Overview

This system requires three main phases:
1. **Data Preparation** (Manual - not in notebooks)
2. **Infrastructure Setup** (Prerequisites notebook)
3. **Agent Deployment** (Agent notebook)

## 📋 Phase 1: Data Preparation (REQUIRED FIRST STEP)

**⚠️ CRITICAL**: This phase is NOT included in the Prerequisites notebook and must be completed manually first.

### 1.1 Create S3 Bucket

```bash
# Replace <YOUR_REGION> with your AWS region (e.g., us-east-1)
aws s3 mb s3://YOUR_S3_BUCKET --region <YOUR_REGION>
```

### 1.2 Copy Sample Data

```bash
# Copy reference genome (publicly available)
# Note: You'll reference this in the Prerequisites notebook
# s3://1000genomes-dragen/reference/hg38_alt_aware_nohla.fa

# Copy sample VCF files to your bucket
aws s3 cp s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21135.hard-filtered.vcf.gz s3://YOUR_S3_BUCKET/YOUR_PREFIX/

# Optional: Copy additional samples
aws s3 cp s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21137.hard-filtered.vcf.gz s3://YOUR_S3_BUCKET/YOUR_PREFIX/
aws s3 cp s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21141.hard-filtered.vcf.gz s3://YOUR_S3_BUCKET/YOUR_PREFIX/
```

### 1.3 Verify Data Upload

```bash
# Verify files are uploaded correctly
aws s3 ls s3://YOUR_S3_BUCKET/YOUR_PREFIX/ --recursive

# Check file sizes (should be several hundred MB each)
aws s3 ls s3://YOUR_S3_BUCKET/YOUR_PREFIX/ --recursive --human-readable
```

## 📋 Phase 2: Infrastructure Setup

### 2.1 Prepare Environment

1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd 26-advanced-vcf-interprter-agent
   ```

2. **Install Dependencies**:
   ```bash
   pip install jupyter boto3 pandas
   ```

3. **Configure AWS CLI**:
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, Region, and Output format
   ```

### 2.2 Replace Configuration Placeholders

1. **Review Required Placeholders**:
   ```bash
   cat CONFIGURATION_PLACEHOLDERS.md
   ```

2. **Get Your AWS Account Information**:
   ```bash
   # Get your AWS Account ID
   aws sts get-caller-identity --query Account --output text
   
   # Get your current region
   aws configure get region
   
   # List available KMS keys
   aws kms list-keys --query 'Keys[*].KeyId' --output table
   ```

3. **Replace Placeholders in Files**:
   - Open each file and replace placeholders with your actual values
   - Key files to update:
     - `Prerequisites_creation.ipynb`
     - `vcf_genomic_functions.py`
     - `vcf-agent-supervisor-agentcore.ipynb`

4. **Verify Placeholder Replacement**:
   ```bash
   ./verify_placeholders.sh
   ```

### 2.3 Run Prerequisites Notebook

1. **Start Jupyter**:
   ```bash
   jupyter notebook Prerequisites_creation.ipynb
   ```

2. **Execute Cells in Order**:
   - **Cell 1**: Set AWS profile
   - **Cell 2**: Create DynamoDB table
   - **Cell 3**: Create IAM role
   - **Cell 4**: Create HealthOmics reference store
   - **Cell 5**: Create HealthOmics variant store
   - **Cell 6**: Deploy Lambda function
   - **Cell 7**: Configure S3 event notifications
   - **Cell 8**: Set up EventBridge scheduler
   - **Cell 9**: Configure Lake Formation permissions

3. **Verify Each Step**:
   - Check AWS console after each major step
   - Verify resources are created successfully
   - Note down resource IDs for later use

### 2.4 Test Infrastructure

1. **Upload Test File**:
   ```bash
   # This should trigger the Lambda function
   aws s3 cp s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21135.hard-filtered.vcf.gz s3://YOUR_S3_BUCKET/YOUR_PREFIX/test-upload.hard-filtered.vcf.gz
   ```

2. **Monitor Processing**:
   ```bash
   # Check Lambda logs
   aws logs tail /aws/lambda/VcfProcessor3 --follow
   
   # Check DynamoDB table
   aws dynamodb scan --table-name VcfImportTracking3
   ```

## 📋 Phase 3: Agent Deployment

### 3.1 Prepare Agent Environment

1. **Install Strands Framework**:
   ```bash
   pip install strands-agents strands-agents-tools
   pip install boto3>=1.37.1
   ```

2. **Create Agent IAM Role**:
   ```bash
   python create_agent_role.py
   ```

### 3.2 Configure Agent Notebook

1. **Open Agent Notebook**:
   ```bash
   jupyter notebook vcf-agent-supervisor-agentcore.ipynb
   ```

2. **Update Configuration**:
   - Replace AWS account ID and region
   - Update database and table names
   - Configure Bedrock model preferences

### 3.3 Deploy Agent

1. **Execute Notebook Cells**:
   - **Cell 1**: Import dependencies and configure AWS
   - **Cell 2**: Initialize genomic analysis functions
   - **Cell 3**: Create Strands agent
   - **Cell 4**: Deploy to AgentCore runtime
   - **Cell 5**: Test agent functionality

2. **Verify Deployment**:
   - Check AgentCore console
   - Test agent with sample queries
   - Verify data access permissions

## 📋 Phase 4: Testing and Validation

### 4.1 End-to-End Testing

1. **Upload New VCF File**:
   ```bash
   aws s3 cp s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21137.hard-filtered.vcf.gz s3://YOUR_S3_BUCKET/YOUR_PREFIX/
   ```

2. **Monitor Processing Pipeline**:
   ```bash
   # Watch Lambda logs
   aws logs tail /aws/lambda/VcfProcessor3 --follow
   
   # Check import job status
   aws omics list-variant-import-jobs --max-results 5
   ```

3. **Test Agent Queries**:
   ```python
   # In the agent notebook
   response = agent.run("List available patients in the database")
   response = agent.run("Show me pathogenic variants for patient NA21135")
   ```

### 4.2 Validation Checklist

- [ ] S3 bucket created and VCF files uploaded
- [ ] DynamoDB table created and accessible
- [ ] IAM roles created with proper permissions
- [ ] HealthOmics reference store created
- [ ] HealthOmics variant store created with analytics enabled
- [ ] Lambda function deployed and triggered by S3 events
- [ ] EventBridge scheduler configured for status checks
- [ ] Lake Formation permissions configured
- [ ] Agent deployed to AgentCore runtime
- [ ] Agent can query genomic data successfully
- [ ] End-to-end pipeline processes VCF files correctly

## 🔧 Troubleshooting Common Issues

### Infrastructure Issues

1. **Lambda Function Not Triggered**:
   - Check S3 event notification configuration
   - Verify Lambda function permissions
   - Check CloudTrail for S3 events

2. **HealthOmics Import Failures**:
   - Verify VCF file format and compression
   - Check reference genome compatibility
   - Validate S3 bucket permissions

3. **Athena Query Failures**:
   - Ensure analytics is enabled on variant store
   - Check Lake Formation resource links
   - Verify Glue catalog permissions

### Agent Issues

1. **Agent Deployment Failures**:
   - Check IAM role permissions
   - Verify Bedrock model access
   - Check CodeBuild logs

2. **Agent Query Failures**:
   - Verify data is available in Athena
   - Check DynamoDB permissions
   - Validate network connectivity

## 📞 Getting Help

1. **Check Logs**:
   - CloudWatch logs for Lambda function
   - AgentCore logs for agent runtime
   - CloudTrail for API calls

2. **Verify Permissions**:
   - IAM roles and policies
   - Lake Formation permissions
   - S3 bucket policies

3. **Review Documentation**:
   - AWS HealthOmics documentation
   - Strands framework documentation
   - This repository's README and troubleshooting sections

## 🎉 Success Criteria

Your implementation is successful when:
1. VCF files uploaded to S3 automatically trigger processing
2. Import jobs complete successfully in HealthOmics
3. Data becomes available in Athena for querying
4. Agent responds to natural language queries about genomic data
5. End-to-end pipeline processes new VCF files without manual intervention

---

**Next Steps**: Once your system is operational, explore advanced features like custom annotations, additional genomic analysis tools, and integration with other AWS services.
