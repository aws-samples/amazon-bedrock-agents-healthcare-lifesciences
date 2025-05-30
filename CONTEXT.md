# CONTEXT.md

This file provides guidance to software development tools when working with code in this repository.

## Repository Overview

This is a healthcare and life sciences AI agents toolkit built on AWS Bedrock, providing specialized agents for drug research, clinical trials, and commercialization workflows. The repository includes individual agents, multi-agent collaboration frameworks, and a React UI for interaction.

## Architecture

### Core Components

- **`agents_catalog/`** - Individual specialized agents (biomarker analysis, medical imaging, clinical evidence research, etc.)
- **`multi_agent_collaboration/`** - Supervisor agents that orchestrate multiple sub-agents for complex workflows
- **`ui/`** - Next.js React application for agent interaction
- **`docs/`** - Astro-based documentation site

### Agent Architecture Pattern

All agents follow a consistent pattern:

- Lambda-based action groups for specific capabilities
- OpenAPI schema definitions for standardized API interactions
- CloudFormation templates for infrastructure deployment
- IAM roles with least-privilege access
- Jupyter notebooks for development and testing

## Development Commands

### Frontend Development

```bash
# React UI
cd ui/
npm install
npm run dev          # Development server with Turbo
npm run build        # Production build
npm run start        # Production server
npm run lint         # ESLint

# Documentation site
cd docs/
npm install
npm run dev          # Astro dev server
npm run build        # Static site build
npm run preview      # Preview build
```

### Infrastructure Deployment

```bash
# Build and package all agents (requires S3_BUCKET env var)
export S3_BUCKET=your-bucket-name
./scripts/build_agents.sh

# Build React app artifacts
./scripts/build_react_app.sh

# Individual agent deployment example
cd agents_catalog/Clinical-trial-protocol-generator-agent/
./deploy.sh BUCKET_NAME STACK_NAME REGION ROLE_ARN
```

### CloudFormation Operations

```bash
# Package templates
aws cloudformation package \
  --template-file template.yaml \
  --s3-bucket bucket-name \
  --output-template-file packaged-template.yaml

# Deploy stack
aws cloudformation deploy \
  --template-file packaged-template.yaml \
  --stack-name stack-name \
  --capabilities CAPABILITY_IAM
```

## Development Standards

### Naming

- Name all folders and files in snakecase (lowercase words separated by an underscore)

### Python Environment

- **Python 3.12** standardized across all components
- Core dependencies: `boto3>=1.35.98`, `awscli`, `botocore`
- Domain-specific packages: `pydicom`, `pyradiomics` (medical imaging), `pandas`, `numpy` (data science)

### Infrastructure Patterns

- CloudFormation templates for all deployments with parameterized stacks
- Multi-stage Docker builds with Alpine Linux base images
- Lambda containers for agent action groups
- ECS deployment for React UI

### Required Configuration

When deploying, these parameters need values:

- **`RedshiftPassword`** - Database password (8+ chars, mixed case + numbers)
- **`ReactAppAllowedCidr`** - IP CIDR for UI access (e.g., `192.0.2.0/32`)
- **`TavilyApiKey`** - Web search API key from tavily.com
- **`USPTOApiKey`** - Patent search API key from USPTO Open Data Portal

## Multi-Agent Collaboration Examples

### Cancer Biomarker Discovery

Combines imaging, database, clinical evidence, and statistical agents for end-to-end biomarker analysis.

### Clinical Trial Protocol Assistant

Integrates protocol generation with study research for comprehensive trial planning.

### Competitive Intelligence

Orchestrates web search, patent, and financial data agents for market analysis.

## Key Files and Patterns

- **`Infra_cfn.yaml`** - Main deployment template
- **`agent_build.yaml`** - Agent build configuration
- **Individual agent folders** - Each contains CloudFormation template, action groups, and Jupyter notebook
- **`action_groups/`** - Lambda functions implementing agent capabilities
- **`deploy.sh`** scripts - Standardized deployment helpers

## Development Workflow

1. Fork repository and update GitHub URLs in config files (`infra_cfn.yaml`, `agent_build.yaml`)
2. Deploy infrastructure using main CloudFormation template
3. Test individual agents via Jupyter notebooks in agent directories
4. Develop custom agents following existing patterns in `agents_catalog/`
5. Use build scripts for packaging and deployment
6. Update documentation using Astro/MDX format

## Model Context Protocol (MCP) Integration

Tavily web search and USPTO search agents can be integrated with MCP clients using the AWS Lambda MCP Server. Configure with AWS credentials and set `FUNCTION_TAG_KEY=Application` and `FUNCTION_TAG_VALUE=HCLSAgents`.
