# CONTEXT.md

This file provides guidance to AI-guided software development tools like Amazon Q Developer (aws.amazon.com/q/developer/build) or Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Amazon Bedrock Agents Healthcare & Life Sciences Toolkit - A comprehensive collection of AI agents built on AWS Bedrock for healthcare workflows including drug research, clinical trials, and commercialization. The project features 13+ specialized agents and multi-agent collaboration frameworks.

## Architecture

### Core Components

- **`agents_catalog/`** - Individual specialized agents (biomarker analysis, clinical evidence, pathology, etc.)
- **`multi_agent_collaboration/`** - Supervisor agents orchestrating multiple sub-agents for complex workflows
- **`ui/`** - Next.js React application with chat interfaces for agent interaction
- **`docs/`** - Astro-based documentation site with Starlight theme

### Agent Architecture Pattern

All agents follow consistent structure:

- Lambda-based action groups for specific capabilities
- CloudFormation templates for infrastructure deployment
- IAM roles with least-privilege access
- Jupyter notebooks for testing and demonstration

### Multi-Agent Supervisor Pattern

- Supervisor agents orchestrate specialized sub-agents
- Shared knowledge bases via Amazon OpenSearch and Redshift
- Asynchronous workflows for complex processing (imaging, pathology)

## Common Development Commands

### Frontend Development

```bash
# React UI (ui/)
npm run dev          # Development server with Turbopack
npm run build        # Production build
npm run start        # Production server
npm run lint         # ESLint

# Documentation site (docs/)
npm run dev          # Astro dev server
npm run build        # Static site build
npm run preview      # Preview build
```

### Infrastructure and Deployment

```bash
# Build and package all agents
export S3_BUCKET=your-bucket-name
./scripts/build_agents.sh

# Build React app artifacts
./scripts/build_react_app.sh

# Individual agent deployment
cd agents_catalog/[agent-name]/
./deploy.sh BUCKET_NAME STACK_NAME REGION ROLE_ARN

# Deploy main infrastructure stack
aws cloudformation deploy \
  --template-file Infra_cfn.yaml \
  --stack-name hcls-agent-toolkit \
  --capabilities CAPABILITY_IAM
```

## Technology Stack

### Core Technologies

- **Python 3.12** - Standardized across all components
- **Next.js 15** with React 19 and TypeScript for UI
- **AWS Bedrock** for AI agent framework
- **CloudFormation** for Infrastructure as Code
- **Docker** with Alpine Linux base images

### Key Dependencies

- `boto3>=1.35.98`, `awscli`, `botocore` for AWS integration
- Domain-specific: `pydicom`, `pyradiomics`, `pandas`, `numpy`
- Frontend: Tailwind CSS, AWS SDK

## Development Standards

### File and Directory Conventions

- Consistent directory structure across agents
- CloudFormation templates follow `[component]-cfn.yaml` naming

### Required Configuration Parameters

- **`RedshiftPassword`** - Database password (8+ chars, mixed case + numbers)
- **`ReactAppAllowedCidr`** - IP CIDR for UI access
- **`TavilyApiKey`** - Web search API key
- **`USPTOApiKey`** - Patent search API key

### Multi-Modal Data Integration

Several agents handle specialized data types:

- **Medical Imaging Expert** - CT scans with asynchronous processing
- **Pathology Agent** - Whole Slide Images (WSI)
- **Biomarker Database Analyst** - RNA-seq and clinical data integration

### Model Context Protocol (MCP) Integration

- Tavily and USPTO agents available as MCP tools
- AWS Lambda MCP Server integration
- Configurable with AWS credentials and function tags

## Testing and Evaluation

### AgentEval Framework

- YAML configurations for comprehensive testing
- Claude-3 based evaluation with expected results validation
- Test categories: factual accuracy, source citation, guardrail compliance

### Development Workflow

1. Test individual agents via Jupyter notebooks in each agent directory
2. Use build scripts for packaging and deployment
3. Deploy infrastructure using main CloudFormation template
4. Develop custom agents following existing patterns

## Healthcare Compliance Notes

- Legal disclaimers included for clinical use and HIPAA compliance
- Enterprise-grade AWS integration with healthcare-specific considerations
- Comprehensive evaluation frameworks for production-ready deployments
