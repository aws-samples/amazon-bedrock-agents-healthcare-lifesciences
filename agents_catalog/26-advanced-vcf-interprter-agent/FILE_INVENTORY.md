# File Inventory

This document lists all files included in the VCF Processing and Genomic Analysis System repository.

## 📁 Core Files

### Jupyter Notebooks
- **`Prerequisites_creation.ipynb`** - Main infrastructure setup notebook
  - Creates DynamoDB tables, IAM roles, Lambda functions
  - Sets up HealthOmics resources and S3 event triggers
  - Configures Lake Formation permissions

- **`vcf-agent-supervisor-agentcore.ipynb`** - Agent setup and deployment notebook
  - Creates Strands-based genomic analysis agent
  - Configures Bedrock model integration
  - Deploys agent to AWS AgentCore runtime

### Python Files
- **`vcf_genomic_functions.py`** - Core genomic analysis functions
  - AWS client initialization
  - Athena query execution
  - Genomic data analysis utilities

- **`vcf_interpreters.py`** - Strands agent tools and functions
  - Agent tool definitions
  - Query parsing and interpretation
  - Natural language processing for genomic queries

- **`lambda_function_fixed_final.py`** - Lambda function for VCF processing
  - Handles S3 upload events
  - Manages HealthOmics import jobs
  - Updates DynamoDB tracking table

- **`create_agent_role.py`** - IAM role creation script
  - Creates agent execution roles
  - Configures trust policies
  - Attaches necessary permissions

### Configuration Files
- **`runtime_requirements.txt`** - Python dependencies for agent runtime
- **`Dockerfile`** - Container configuration for agent deployment

### Documentation
- **`README.md`** - Main documentation and setup guide
- **`CONFIGURATION_PLACEHOLDERS.md`** - Placeholder replacement guide
- **`Setup_Checklist.md`** - Quick setup checklist
- **`FILE_INVENTORY.md`** - This file inventory

### Architecture and Diagrams
- **`VCF_agent.drawio.png`** - System architecture diagram

### Utility Scripts
- **`verify_placeholders.sh`** - Script to verify placeholder replacement

## 🔍 File Dependencies

### Prerequisites Notebook Dependencies
- `lambda_function_fixed_final.py` - Deployed as Lambda function
- AWS services: DynamoDB, Lambda, HealthOmics, S3, EventBridge

### Agent Notebook Dependencies
- `vcf_genomic_functions.py` - Imported for core analysis functions
- `vcf_interpreters.py` - Imported for agent tools
- `create_agent_role.py` - Used for IAM role creation
- `runtime_requirements.txt` - Used for agent runtime dependencies
- `Dockerfile` - Used for agent containerization

### Runtime Dependencies
- `vcf_genomic_functions.py` - Core analysis functions
- `vcf_interpreters.py` - Agent tools and query processing
- AWS services: Bedrock, Athena, DynamoDB, HealthOmics

## ✅ Verification Checklist

All required files are present:
- [x] Prerequisites_creation.ipynb
- [x] vcf-agent-supervisor-agentcore.ipynb
- [x] vcf_genomic_functions.py
- [x] vcf_interpreters.py
- [x] lambda_function_fixed_final.py
- [x] create_agent_role.py
- [x] runtime_requirements.txt
- [x] Dockerfile
- [x] VCF_agent.drawio.png
- [x] README.md
- [x] CONFIGURATION_PLACEHOLDERS.md
- [x] verify_placeholders.sh

## 📝 Notes

- All files have been sanitized with appropriate placeholders
- No sensitive AWS account information is hardcoded
- Files are ready for public GitHub repository sharing
- Users must replace placeholders before deployment
