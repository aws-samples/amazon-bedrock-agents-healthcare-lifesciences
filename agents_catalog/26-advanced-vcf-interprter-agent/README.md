# VCF Processing and Genomic Analysis System

This repository contains a comprehensive system for processing VCF (Variant Call Format) files using AWS HealthOmics and creating an intelligent genomic analysis agent using the Strands framework. The system consists of two main components:

1. **VCF Processing Infrastructure** - Automated pipeline for importing VCF files into AWS HealthOmics
2. **Genomic Analysis Agent** - AI-powered agent for querying and analyzing genomic data

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup Guide](#setup-guide)
- [Usage](#usage)
- [Components](#components)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## 🔍 Overview

This system enables researchers and clinicians to:
- Automatically process and import VCF files into AWS HealthOmics variant stores
- Track import job statuses in real-time using DynamoDB
- Query genomic data using natural language through an AI agent
- Perform complex genomic analyses including variant interpretation and clinical significance assessment
- Access data through Amazon Athena for advanced analytics

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   S3 Bucket │───▶│    Lambda    │───▶│  DynamoDB   │───▶│    Athena    │
│ (VCF files) │    │ VcfProcessor │    │ (Tracking)  │    │  (Queries)   │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                           │                                       ▲
                           ▼                                       │
                   ┌───────────────┐                      ┌──────────────┐
                   │  HealthOmics  │                      │   Strands    │
                   │ Variant Store │                      │    Agent     │
                   └───────────────┘                      └──────────────┘
                           ▲                                       │
                           │                                       ▼
                   ┌───────────────┐                      ┌──────────────┐
                   │  EventBridge  │                      │   Bedrock    │
                   │ (Scheduler)   │                      │    Models    │
                   └───────────────┘                      └──────────────┘
```

## 📋 Prerequisites

### AWS Account Requirements
- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Python 3.9+ environment
- Jupyter Notebook environment (for setup)

### Required AWS Services
- AWS HealthOmics
- Amazon DynamoDB
- AWS Lambda
- Amazon S3
- Amazon Athena
- AWS Glue
- AWS Lake Formation
- Amazon Bedrock
- Amazon EventBridge

### IAM Permissions
Your AWS user/role needs permissions for:
- HealthOmics (create variant stores, import jobs)
- DynamoDB (create tables, read/write items)
- Lambda (create functions, manage permissions)
- S3 (read VCF files, configure notifications)
- Athena (execute queries)
- Glue (manage data catalog)
- Lake Formation (manage permissions)
- Bedrock (invoke models)

## 🚀 Setup Guide

### Step 1: Infrastructure Setup

1. **Open the Prerequisites Notebook**
   ```bash
   jupyter notebook Prerequisites_creation.ipynb
   ```

2. **Configure AWS Profile**
   - Update the AWS profile in the first cell:
   ```python
   os.environ['AWS_PROFILE'] = 'your-aws-profile'  # Update with your AWS profile
   ```

3. **Run Infrastructure Setup**
   Execute all cells in the Prerequisites notebook to create:
   - DynamoDB table for tracking VCF import jobs
   - IAM role with necessary permissions
   - HealthOmics reference store and variant store
   - Lambda function for processing VCF files
   - S3 event notifications
   - EventBridge rules for scheduled status checks

4. **Update Configuration Variables**
   - **IMPORTANT**: See `CONFIGURATION_PLACEHOLDERS.md` for complete list of values to replace
   - **S3 URI**: Update the S3 bucket path where your VCF files are stored
   - **Variant Store Name**: Note the created variant store name
   - **Reference ARN**: Update with your reference genome ARN
   - **KMS Key**: Update the KMS key ARN in the IAM policy
   - **AWS Account ID**: Replace AWS_ACCOUNT_ID placeholders with your actual account ID

### Step 2: Verify Infrastructure

1. **Check DynamoDB Table**
   - Verify `VcfImportTracking3` table exists
   - Confirm table has `SampleID` as primary key

2. **Verify Lambda Function**
   - Check `VcfProcessor3` function is deployed
   - Confirm environment variables are set correctly
   - Test function permissions

3. **Validate HealthOmics Resources**
   - Confirm variant store is active
   - Verify reference store contains reference genome
   - Check analytics is enabled for Athena queries

### Step 3: Agent Setup

1. **Install Dependencies**
   ```bash
   pip install strands-agents strands-agents-tools
   pip install boto3>=1.37.1
   ```

2. **Open the Agent Notebook**
   ```bash
   jupyter notebook advanced-vcf-interpreter-strands-agents.ipynb
   ```

3. **Configure Agent Settings**
   - Update AWS region and account ID
   - Configure Bedrock model preferences
   - Set database and table names

4. **Initialize the Agent**
   Execute the notebook cells to create the Strands agent with genomic analysis capabilities

## 📖 Usage

### Processing VCF Files

1. **Upload VCF Files**
   - Upload `.hard-filtered.vcf.gz` files to your configured S3 bucket
   - Files should follow the naming convention: `{SampleID}.hard-filtered.vcf.gz`

2. **Monitor Processing**
   - Check DynamoDB table for real-time status updates
   - Monitor CloudWatch logs for detailed processing information
   - Status progression: `SUBMITTED` → `IN_PROGRESS` → `COMPLETED`

3. **Query Data**
   - Once processing completes, data becomes available in Athena
   - Use the Strands agent for natural language queries
   - Access raw data through Athena workbench

### Using the Genomic Analysis Agent

1. **Start the Agent**
   ```python
   # In the agent notebook
   response = agent.run("List available patients in the database")
   ```

2. **Example Queries**
   - "Show me all pathogenic variants for patient SAMPLE_ID_1"
   - "Find variants in the BRCA1 gene across all patients"
   - "What are the clinical significance distributions for patient SAMPLE_ID_2?"
   - "Compare variant counts between patients SAMPLE_ID_1 and SAMPLE_ID_5"

3. **Advanced Analysis**
   - Variant impact assessment
   - Clinical significance interpretation
   - Gene-based variant analysis
   - Population frequency analysis

## 🔧 Components

### 1. Prerequisites_creation.ipynb
**Purpose**: Sets up the complete AWS infrastructure for VCF processing

**Key Functions**:
- Creates DynamoDB tracking table
- Sets up IAM roles and policies
- Deploys Lambda function for VCF processing
- Configures HealthOmics variant and reference stores
- Sets up S3 event notifications
- Creates EventBridge scheduling rules
- Configures Lake Formation permissions

### 2. advanced-vcf-interpreter-strands-agents.ipynb
**Purpose**: Creates an AI-powered genomic analysis agent

**Key Functions**:
- Initializes Strands agent framework
- Configures Bedrock model integration
- Defines genomic analysis tools
- Provides natural language interface for data queries
- Enables complex genomic analysis workflows

### 3. vcf_genomic_functions.py
**Purpose**: Core genomic analysis functions and utilities

**Key Functions**:
- AWS client initialization and configuration
- Genomic data querying and analysis
- Variant significance assessment
- Patient data management
- Athena query execution
- Clinical interpretation logic

### 4. lambda_function_fixed_final.py
**Purpose**: Lambda function for processing VCF import jobs

**Key Functions**:
- Handles S3 upload events
- Starts HealthOmics import jobs
- Tracks job status in DynamoDB
- Manages Lake Formation permissions
- Provides status checking and updates

## 🔍 Troubleshooting

### Common Issues

#### 1. Lambda Function Errors
**Symptoms**: Import jobs not starting, status not updating
**Solutions**:
- Check CloudWatch logs: `/aws/lambda/VcfProcessor3`
- Verify IAM permissions for HealthOmics and DynamoDB
- Confirm environment variables are set correctly
- Check S3 event notification configuration

#### 2. Athena Query Failures
**Symptoms**: "Table not found" or permission errors
**Solutions**:
- Verify Lake Formation resource links are created
- Check Athena workgroup uses Engine Version 3
- Confirm analytics is enabled on variant store
- Validate Glue catalog permissions

#### 3. Agent Connection Issues
**Symptoms**: Agent cannot connect to AWS services
**Solutions**:
- Verify AWS credentials and region configuration
- Check Bedrock model access permissions
- Confirm DynamoDB and Athena permissions
- Validate network connectivity

#### 4. VCF Import Failures
**Symptoms**: Jobs stuck in SUBMITTED or fail immediately
**Solutions**:
- Check VCF file format and compression
- Verify S3 bucket permissions
- Confirm reference genome compatibility
- Check HealthOmics service limits

### Debugging Commands

```bash
# Check DynamoDB table contents
aws dynamodb scan --table-name VcfImportTracking3 --output table

# Test Lambda function
aws lambda invoke --function-name VcfProcessor3 --payload '{"check_status": true}' response.json

# Check EventBridge rule
aws events describe-rule --name VcfStatusCheckSchedule

# Verify S3 notifications
aws s3api get-bucket-notification-configuration --bucket YOUR_S3_BUCKET_NAME

# Check Athena workgroups
aws athena list-work-groups
```

## 🔒 Security Considerations

### Data Protection
- VCF files contain sensitive genomic information
- Ensure S3 buckets have appropriate access controls
- Use encryption at rest and in transit
- Implement proper IAM policies with least privilege

### Access Control
- Limit Bedrock model access to authorized users
- Use Lake Formation for fine-grained data permissions
- Implement proper authentication for agent access
- Monitor access logs and usage patterns

### Compliance
- Consider HIPAA compliance for healthcare data
- Implement data retention policies
- Ensure audit logging is enabled
- Follow organizational data governance policies

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review CloudWatch logs for detailed error information
3. Verify AWS service limits and quotas
4. Consult AWS HealthOmics documentation
5. Check Strands framework documentation

## 📝 Notes

- The system is designed for research and clinical genomics workflows
- Processing time varies based on VCF file size and complexity
- Athena queries may take time for large datasets
- Agent responses depend on data availability and quality
- Regular monitoring of AWS costs is recommended

---

**Last Updated**: August 2025
**Version**: 1.0
**Compatibility**: AWS HealthOmics, Python 3.9+, Strands Framework
