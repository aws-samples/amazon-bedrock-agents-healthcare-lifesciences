# Genomics VEP Pipeline and Variant Interpreter Agent

This repository contains a comprehensive system for processing VCF (Variant Call Format) files using AWS HealthOmics with VEP (Variant Effect Predictor) annotation and creating an intelligent genomic analysis agent using the Strands framework. The system consists of two main components:

1. **Genomics VEP Pipeline Infrastructure** - Automated pipeline for processing VCF files with VEP annotation in AWS HealthOmics
2. **Genomic Variant Interpreter Agent** - AI-powered agent for querying and analyzing annotated genomic data with Streamlit interface

## 📋 Table of Contents 

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Initial Setup Requirements](#initial-setup-requirements)
- [Sample Data](#sample-data)
- [Complete Setup Guide](#complete-setup-guide)
- [Usage](#usage)
- [Components](#components)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## 🔍 Overview

This system enables researchers and clinicians to:
- Automatically process and annotate VCF files using VEP in AWS HealthOmics workflows
- Track processing job statuses in real-time using Amazon DynamoDB
- Query genomic data using natural language through an AI agent
- Perform complex genomic analyses including variant interpretation and clinical significance assessment
- Access data through Amazon Athena for advanced analytics
- Interact with genomic data through an intuitive Streamlit web interface

## 🏗️ Architecture

![Genomics VEP Pipeline Architecture](advanced-strands-agentcore/static/VCF_agent_fin.drawio.png)

## 🔬 Agent view

![Genomics Agent View](advanced-strands-agentcore/streamlit_screenshot.png)

The system follows this workflow:
1. **Data Preparation**: VEP cache files are uploaded to Amazon Simple Storage Service (Amazon S3) buckets; Import reference sequences into healthomics reference store 
2. **Container Setup**: VEP Docker image is pushed to ECR for workflow execution
3. **Event-Driven Processing**: S3 events trigger AWS Lambda function for automated processing
4. **HealthOmics Integration**: AWS Lambda creates VEP annotation workflows in HealthOmics
5. **Status Tracking**: Amazon DynamoDB tracks job progress and status updates
6. **Data Analytics**: Processed data becomes available in Athena for querying
7. **AI Agent Interface**: Strands-based agent provides natural language access to genomic data
8. **Web Interface**: Streamlit app provides user-friendly interaction with the agent

## 📋 Prerequisites

### AWS Account Requirements
- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Python 3.9+ environment
- Docker installed for container operations
- Jupyter Notebook environment (for setup)

### Required AWS Services
- AWS HealthOmics
- Amazon DynamoDB
- AWS Lambda
- Amazon S3
- Amazon ECR
- Amazon Athena
- AWS Glue
- AWS Lake Formation
- Amazon Bedrock
- Amazon EventBridge
- AWS Batch
- AWS Step Functions

### IAM Permissions
Your AWS user/role needs permissions for:
- HealthOmics (create reference store, variant stores, annotation stores, workflows)
- DynamoDB (create tables, read/write items)
- Lambda (create functions, manage permissions)
- S3 (read VCF files, configure notifications)
- ECR (push/pull Docker images)
- Athena (execute queries)
- Glue (manage data catalog)
- Lake Formation (manage permissions)
- Bedrock (invoke models)
- Batch (create job definitions and queues)
- Step Functions (create and execute state machines)

## 🚀 Healthomics pre-requisites setup for workflows and sequence store

### Step 0: VEP Cache and Docker Setup

**⚠️ Important**: Complete these steps before running any notebooks.

#### 1. Download and Prepare VEP Cache Files

```bash
# Download VEP cache for GRCh38
curl -O https://ftp.ensembl.org/pub/release-111/variation/indexed_vep_cache/homo_sapiens_vep_111_GRCh38.tar.gz

# Extract cache files
tar xzf homo_sapiens_vep_111_GRCh38.tar.gz

# Upload to your S3 bucket (replace with your bucket name)
aws s3 cp homo_sapiens_vep_111_GRCh38.tar.gz s3://YOUR_VEP_CACHE_BUCKET/cache/
aws s3 sync homo_sapiens_vep_111_GRCh38/ s3://YOUR_VEP_CACHE_BUCKET/cache/homo_sapiens_vep_111_GRCh38/ --recursive
```

#### 2. Setup VEP Docker Container

```bash
# Pull the official VEP Docker image
docker pull ensemblorg/ensembl-vep:113.4

# Login to ECR (replace <account_id> and <region_info> with your values)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.<region_info>.amazonaws.com
aws ecr create-repository --repository-name ensemblorg
# Tag the image for ECR
docker tag ensemblorg/ensembl-vep:113.4 <account_id>.dkr.ecr.<region_info>.amazonaws.com/genomics-vep:113.4

# Push to ECR
docker push <account_id>.dkr.ecr.<region_info>.amazonaws.com/genomics-vep:113.4
```

**Note**: Replace `<account_id>`, `<region_info>`, and `<docker_uri>` with your actual AWS account ID, region, and ECR repository URI.

### Download Clinvar annotation for disease/drug-specific evidence

```bash
wget https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar_20250810.vcf.gz
aws s3 cp clinvar_20250810.vcf.gz s3://<YOUR_CLINVAR_BUCKET>/clinvar20250810/
SOURCE_ANNOTATION_URI = f"s3://<YOUR_CLINVAR_BUCKET>/clinvar20250810/clinvar_20250810.vcf.gz"
```

### Reference Genome
You can use the publicly available reference genome from the 1000 Genomes project:

```bash
# Reference genome location (publicly accessible)
aws s3 cp s3://1000genomes-dragen/reference/hg38_alt_aware_nohla.fa .
```

### Build reference sequence file mapping in Healthomics reference store 
This should be the reference sequence used to generate vcf files for healthomics analytics mapping

#### Create reference store if not available, please note you can create one reference store per account [If the reference store is not created, the later step cloudformation template will create one, but we recommend to perform the step here and import your preferred reference sequence fasta file as shown below]

```bash
aws omics create-reference-store \
    --name "my-reference-store" \
    --description "Reference store for genomic analysis"
```
### Import Reference FASTA

```bash
aws omics start-reference-import-job \
    --reference-store-id <reference-store-id> \
    --role-arn arn:aws:iam::<account-id>:role/<omics-service-role> \
    --sources sourceFile=s3://<bucket>/<path>/reference.fasta,name="GRCh38",description="Human reference genome"
```

### Check Import Status

```bash
aws omics get-reference-import-job \
    --reference-store-id <reference-store-id> \
    --job-id <import-job-id>
```

## 🚀 VEP pipeline Setup and event triggers deployment Guide
You need to perform 2 major deployments: 

1. **Infrastructure depolyment will create:** S3 input/output buckets, healthomics variant store, healthomics annotation store, Lakeformation database to establish resource link, healthomics reference store (if not created), KMS encryption keys [true/false to use existing key] and, IAM role needed for healthomics workflow, lambda functions and agent role. 
2. **VEP pipeline deployment and event triggers through Jupyter notebook guidance:** Extract the output values from cloudformation template, create VEP workflow from zipped VEP worlflow folder, vcf processor and monitor functions from lambda folder, create s3 event triggers, event bridge setups for healthomics workflows and healthomics analytics import automation,  create resource links to the database in lakeformation and testing few before athena queries. 

### Step 1: Infrastructure Deployment

#### A: Using CloudFormation Template

1. **Deploy Infrastructure**:
```bash
aws cloudformation deploy \
   --template-file advanced-strands-agentcore/prerequisite/infrastructure.yaml \
   --stack-name genomics-vep-pipeline \
   --capabilities CAPABILITY_IAM 
```

2. **Monitor Stack Creation**:
```bash
aws cloudformation describe-stacks --stack-name genomics-vep-pipeline
```

#### B: Using Jupyter Notebook

1. **Open the Infrastructure Notebook**:
```bash
jupyter notebook advanced-strands-agentcore/prerequisite/genomics-vep-pipeline-deployment-complete.ipynb
```

2. **Configure AWS Profile** (First cell in notebook):
```python
os.environ['AWS_PROFILE'] = 'your-aws-profile'  # Update with your AWS profile
```

3. **Update Configuration Variables**:
   - **S3 Bucket Names**: Update VCF input and VEP output bucket names
   - **AWS Account ID**: Replace `<YOUR_ACCOUNT_ID>` placeholders
   - **AWS Region**: Replace `<YOUR_REGION>` with your AWS region
   - **ECR Repository URI**: Update Docker image URI
   - **KMS Key**: Update the KMS key ARN in policies

4. **Run Infrastructure Setup**:
   Execute all cells to create:
   - S3 buckets for VCF input and VEP output
   - DynamoDB table for tracking jobs
   - IAM roles with necessary permissions
   - HealthOmics variant and annotation stores
   - Lambda function for processing
   - ECR repository for VEP container
   - Lake Formation database and permissions

### Step 2: Verify Infrastructure

1. **Check S3 Buckets**:
   ```bash
   aws s3 ls | grep genomics
   ```

2. **Verify DynamoDB Table**:
   ```bash
   aws dynamodb describe-table --table-name genomics-job-tracking
   ```

3. **Validate HealthOmics Resources**:
   ```bash
   # List variant stores
   aws omics list-variant-stores
   
   # List annotation stores
   aws omics list-annotation-stores
   ```

4. **Check ECR Repository**:
   ```bash
   aws ecr describe-repositories --repository-names ensemblorg
   ```

### Step 3: Agent and Streamlit Setup

**⚠️ Important**: Use the `advanced-strands-agentcore/` directory for the latest implementation. The `bedrock_agent/` directory contains the old implementation and will be deprecated soon.

**Agent Creation**: Run setup_environment.py script to set the environment before using `advanced-strands-agentcore/agent/main.py` and update `advanced-strands-agentcore/app.py` as below for setting up Agent Runtime

## Create Memory (Optional)
```bash
python scripts/agentcore_memory.py create --name researchapp
```

## Setup Environment for Agent Runtime
The following script execution make sure all required modules and functions imported as shown in 'advanced-strands-agentcore/agent/genomics-store-agent-supervisor-agentcore.ipynb' notebook section **Import required libraries and initialize AWS clients**

```bash
python agent/setup_environment.py
```

```bash
agentcore configure --entrypoint agent/main.py -er arn:aws:iam::<Account-Id>:role/<Role> --name genomicsappapp<AgentName>
```

3. **AgentCore Deployment**: Deploy the agent to Bedrock AgentCore Runtime

```bash
agentcore launch
```

### 4. User Interface

Install and run the Streamlit interface:

```bash
# Install dependencies
pip install -r advanced-strands-agentcore/requirements.txt
pip install -r advanced-strands-agentcore/streamlit_requirements.txt

# Run Streamlit app [Make sure you modified agent_arn in app.py]
streamlit run app.py --server.port 8501
```

### Step 5: Test the Complete System

#### Sample Data
Sample VCF files are available from the 1000 Genomes project. Copy them to your S3 bucket:

You may use 1000 Genomes Project data for testing:

1. **Upload a Test VCF File**:
```bash
# This should trigger the Lambda function automatically
aws s3 cp s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21135.hard-filtered.vcf.gz s3://YOUR_VCF_INPUT_BUCKET/
```

#### Additional sample files (optional)

```bash
aws s3 cp s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21137.hard-filtered.vcf.gz s3://YOUR_VCF_INPUT_BUCKET/
aws s3 cp s3://1000genomes-dragen/data/dragen-3.5.7b/hg38_altaware_nohla-cnv-anchored/NA21141.hard-filtered.vcf.gz s3://YOUR_VCF_INPUT_BUCKET/
```
**Important**: Replace `YOUR_VCF_INPUT_BUCKET` with your actual S3 bucket name for VCF input files.


2. **Monitor Processing**:
```bash
# Check DynamoDB for job status
aws dynamodb scan --table-name genomics-job-tracking
   
# Check Lambda logs
aws logs tail /aws/lambda/genomics-vep-processor --follow
```

3. **Test Agent Queries**:
   - Use Streamlit interface to query: "List available patients in the database"
   - Or use notebook: `response = agent.run("Show me variants for patient NA21135")`

## 📖 Usage

### Processing VCF Files

1. **Upload VCF Files**:
   - Upload `.vcf.gz` files to your configured S3 input bucket
   - Files should follow the naming convention: `{SampleID}.hard-filtered.vcf.gz`
   - The system will automatically detect and process new files with VEP annotation

2. **Monitor Processing**:
   - Check DynamoDB table for real-time status updates
   - Monitor CloudWatch logs for detailed processing information
   - Status progression: `SUBMITTED` → `RUNNING` → `COMPLETED`

3. **Query Data**:
   - Once processing completes, annotated data becomes available in Athena
   - Use the Strands agent through Streamlit interface for natural language queries
   - Access raw data through Athena workbench

### Using the Genomic Variant Interpreter Agent

#### Through Streamlit Interface (Recommended)

1. **Launch Streamlit**:
```bash
streamlit run app.py
```

2. **Example Queries**:
   - "How many patients are in the present cohort?",
   - "Analyze chromosome 17 variants in patient NA21135?",
   - "What's the frequency of chr13:32332591 in BRCA2 variant in this cohort and 1000 genome cohort(1000g)?",
   - "Can you check how many variants are present for BRCA family of genes in patient NA21135?",
   - "Analyze patient NA21135 for risk stratification",
   - "Which are the major drug related impactful variant pathway enriched in this patients cohort and give me the patient IDs who have the variants in those pharmacogenomics pathway?"

#### Through Jupyter Notebook

1. **Start the Agent**:
```python
# In the agent notebook
response = agent.run("List available patients in the database")
```

2. **Advanced Analysis**:
   - Variant impact assessment with VEP annotations
   - Clinical significance interpretation
   - Gene-based variant analysis
   - Population frequency analysis
   - Consequence type analysis

## 🔧 Components

### 1. infrastructure.yaml
**Purpose**: CloudFormation template for automated basic infrastructure deployment

**Key Functions**:
- Defines basic AWS resources as Infrastructure as Code
- Creates S3 buckets with proper configurations
- Sets up IAM roles and policies
- Configures DynamoDB tables
- Creates Lake Formation database
- Establishes proper resource dependencies


### 2. genomics-vep-pipeline-deployment-complete.ipynb
**Purpose**: Sets up the complete AWS infrastructure for VEP-enabled genomic processing

**Key Functions**:
- Creates S3 buckets for input and output
- Sets up DynamoDB tracking table
- Deploys IAM roles and policies
- Creates HealthOmics variant and annotation stores
- Configures Lambda function for VEP processing
- Sets up ECR repository for VEP container
- Configures Lake Formation permissions
- Creates EventBridge scheduling rules

### 3. main.py to create genomics-store-agent-supervisor-agentcore
**Purpose**: Creates an AI-powered genomic variant interpreter agent with Streamlit interface

**Key Functions**:
- Initializes Strands agent framework
- Configures Bedrock model integration
- Defines genomic analysis tools with VEP annotation support
- Provides natural language interface for data queries
- Enables complex genomic analysis workflows
- Integrates with Streamlit for web-based interaction


### 4. app_modules/genomics_store_functions.py
**Purpose**: Core genomic analysis functions and utilities

**Key Functions**:
- AWS client initialization and configuration
- Genomic data querying and analysis with VEP annotations
- Variant significance assessment
- Patient data management
- Athena query execution
- Clinical interpretation logic

### 5. app_modules/genomics_store_interpreters.py
**Purpose**: Strands agent tools and genomic analysis functions

**Key Functions**:
- Agent tool definitions for genomic queries
- Query parsing and interpretation
- Integration with core genomic functions
- Natural language processing for genomic queries
- VEP annotation data handling

### 6. app.py
**Purpose**: Streamlit web interface for the genomic analysis agent

**Key Functions**:
- Web-based chat interface
- AWS configuration management
- Real-time agent interaction
- Query history and session management
- Responsive UI for genomic data exploration

### 7. scripts/create_agent_role.py
**Purpose**: Creates IAM roles for the Strands agent

**Key Functions**:
- Creates IAM roles with appropriate permissions
- Configures trust policies for Bedrock and Lambda
- Attaches managed and custom policies

## 🔍 Troubleshooting

### Common Issues

#### 1. VEP Container Issues
**Symptoms**: Workflow fails during VEP annotation step
**Solutions**:
- Verify ECR repository contains VEP image
- Check VEP cache files are properly uploaded to S3
- Confirm container has proper permissions
- Validate VEP cache version compatibility

#### 2. Lambda Function Errors
**Symptoms**: VEP workflows not starting, status not updating
**Solutions**:
- Check CloudWatch logs: `/aws/lambda/genomics-vep-processor`
- Verify IAM permissions for HealthOmics and DynamoDB
- Confirm environment variables are set correctly
- Check S3 event notification configuration

#### 3. Athena Query Failures
**Symptoms**: "Table not found" or permission errors
**Solutions**:
- Verify Lake Formation resource links are created
- Check Athena workgroup configuration
- Confirm analytics is enabled on variant store
- Validate Glue catalog permissions

#### 4. Streamlit Connection Issues
**Symptoms**: Agent cannot connect to AWS services
**Solutions**:
- Verify AWS credentials in Streamlit interface
- Check Bedrock model access permissions
- Confirm DynamoDB and Athena permissions
- Validate network connectivity

#### 5. VCF Processing Failures
**Symptoms**: Jobs stuck in SUBMITTED or fail immediately
**Solutions**:
- Check VCF file format and compression
- Verify S3 bucket permissions
- Confirm reference genome compatibility
- Check HealthOmics service limits
- Validate VEP cache accessibility

### Debugging Commands

```bash
# Check DynamoDB table contents
aws dynamodb scan --table-name genomics-job-tracking --output table

# Test Lambda function
aws lambda invoke --function-name genomics-vep-processor --payload '{"test": true}' response.json

# Check HealthOmics workflows
aws omics list-workflows --type PRIVATE

# Verify ECR images
aws ecr list-images --repository-name genomics-vep

# Monitor Lambda logs in real-time
aws logs tail /aws/lambda/genomics-vep-processor --follow

# Check HealthOmics annotation jobs
aws omics list-annotation-import-jobs --max-results 10

# Verify S3 bucket contents
aws s3 ls s3://YOUR_VCF_INPUT_BUCKET/ --recursive
aws s3 ls s3://YOUR_VEP_OUTPUT_BUCKET/ --recursive
```

## 🔒 Security Considerations

### Data Protection
- VCF files contain sensitive genomic information
- Ensure S3 buckets have appropriate access controls
- Use encryption at rest and in transit
- Implement proper IAM policies with least privilege
- Secure VEP cache files and container images

### Access Control
- Limit Bedrock model access to authorized users
- Use Lake Formation for fine-grained data permissions
- Implement proper authentication for agent access
- Monitor access logs and usage patterns
- Secure Streamlit interface with proper authentication

### Compliance
- Consider HIPAA compliance for healthcare data
- Implement data retention policies
- Ensure audit logging is enabled
- Follow organizational data governance policies
- Maintain container image security

## Cleanup

```bash
chmod +x advanced-strands-agentcore/scripts/cleanup.sh

python advanced-strands-agentcore/scripts/agentcore_memory.py delete
.advanced-strands-agentcore/scripts/cleanup.sh
```

For issues and questions:
1. Check the troubleshooting section above
2. Review CloudWatch logs for detailed error information
3. Verify AWS service limits and quotas
4. Consult AWS HealthOmics documentation
5. Check Strands framework documentation
6. Review VEP documentation for annotation issues

## 📝 Notes

- The system is designed for research and clinical genomics workflows
- VEP annotation processing time varies based on VCF file size and complexity
- Athena queries may take time for large datasets
- Agent responses depend on data availability and quality
- Regular monitoring of AWS costs is recommended
- Ensure VEP cache files are properly configured before processing
- Container images should be kept updated for security

## 📚 Additional Resources

- [AWS HealthOmics Documentation](https://docs.aws.amazon.com/omics/)
- [Strands Framework Documentation](https://github.com/awslabs/strands)
- [VEP Documentation](https://ensembl.org/info/docs/tools/vep/index.html)
- [VCF Format Specification](https://samtools.github.io/hts-specs/VCFv4.2.pdf)
- [1000 Genomes Project](https://www.internationalgenome.org/)
- [Ensembl VEP Cache Files](https://ftp.ensembl.org/pub/release-111/variation/indexed_vep_cache/)

---

**Last Updated**: September 2025
**Version**: 2.0
**Compatibility**: AWS HealthOmics, Python 3.9+, Strands Framework, VEP 113.4
