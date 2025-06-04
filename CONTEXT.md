# CONTEXT.md

This file provides guidance to coding agents such as Claude Code (claude.ai/code) or Amazon Q Developer when working with code in this repository.

## Repository Overview

This is the AWS Healthcare and Life Sciences Agents Toolkit - a collection of specialized Amazon Bedrock agents for drug research, clinical trials, and commercialization workflows. The repository contains three main components:

- **agents_catalog/**: Library of 18+ specialized agents (biomarker analysis, clinical research, pathology, etc.)
- **multi_agent_collaboration/**: Framework for coordinating multiple agents on complex workflows
- **ui/**: Next.js React application providing a web interface to interact with deployed agents

## Architecture

### Agent Structure

Each agent follows a consistent pattern:

- CloudFormation template (`.yaml`) for infrastructure deployment
- Action groups in `/action-groups/` directories containing Lambda function implementations  
- README with deployment instructions and usage examples
- Optional Jupyter notebooks (`.ipynb`) for interactive development

### Foundation Models

- Primary: Claude 3.5 Sonnet (`us.anthropic.claude-3-5-sonnet-20241022-v2:0`)
- Alternative: Amazon Nova Pro (`us.amazon.nova-pro-v1:0`)
- Models are parameterized in CloudFormation templates

### Multi-Agent Coordination

Uses supervisor agent pattern where a coordinator orchestrates specialized sub-agents. Example: Cancer Biomarker Discovery supervisor coordinates biomarker analyst, imaging expert, statistician, and clinical researcher agents.

## Development Commands

### UI Application (Next.js)

```bash
cd ui/
npm run dev          # Start development server with turbopack
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run linting
```

### Documentation Site (Astro)

```bash
cd docs/
npm run dev          # Start development server
npm run build        # Build static site
npm run preview      # Preview built site
```

### AWS Deployment

```bash
# Deploy main infrastructure stack
aws cloudformation deploy --template-file Infra_cfn.yaml \
  --capabilities CAPABILITY_IAM \
  --stack-name hcls-agents-toolkit \
  --parameter-overrides \
    RedshiftPassword="YourPassword123" \
    ReactAppAllowedCidr="192.0.2.0/24" \
    TavilyApiKey="your-tavily-key" \
    USPTOApiKey="your-uspto-key"

# Individual agent deployment
aws cloudformation deploy --template-file agents_catalog/[agent-name]/[agent-name]-cfn.yaml \
  --capabilities CAPABILITY_IAM \
  --stack-name [agent-stack-name]
```

## Key Infrastructure Components

### Required AWS Services

- **Amazon Bedrock**: Foundation models (Claude, Nova)
- **Lambda**: Action group implementations
- **S3**: Artifact storage and data input/output
- **CloudFormation**: Infrastructure as code
- **IAM**: Granular permissions for agent actions
- **Redshift**: Clinical/genomic data storage (biomarker agents)
- **OpenSearch**: Document search capabilities

### External Dependencies

- **Tavily API**: Web search functionality
- **USPTO API**: Patent search capabilities
- **SageMaker**: Some agents use marketplace models (JSL Medical NLP)

## Agent Development Patterns

### Lambda Action Groups

Standard handler structure:

```python
def lambda_handler(event, context):
    parameters = event.get('parameters', [])
    # Extract and validate parameters
    # Execute business logic
    return {
        'response': {
            'actionGroup': event['actionGroup'],
            'function': event['function'],
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': result_text
                    }
                }
            }
        }
    }
```

### Docker Containers

For complex processing (e.g., semantic search, image analysis):

- Use ECR for container storage
- Multi-stage builds for dependency optimization
- Environment variable configuration

### OpenAPI Schema Definition

Action groups require OpenAPI 3.0 schemas defining available tools and parameters.

## Testing

### Agent Evaluation

Use the evaluation framework in `evaluations/`:

- Run `evaluate_biomarker_agent.ipynb` for comprehensive testing
- Includes RAG, Text-to-SQL, and Chain-of-Thought evaluations
- Results tracked in Langfuse dashboards

### Individual Agent Testing

- Deploy with CloudFormation templates
- Test via Jupyter notebooks in agent directories
- Use Bedrock console for direct invocation testing

## Important Notes

### Model Access

Ensure access to required Bedrock models:

- Amazon Titan Embeddings G1 - Text
- Amazon Nova Pro
- Anthropic Claude 3.5 Sonnet (all versions)

### Quota Limits

Request increase for "Parameters per function" quota to at least 10 in Amazon Bedrock.

### Security

- Never commit API keys or sensitive credentials
- Use CloudFormation parameters with NoEcho for secrets
- Implement least-privilege IAM policies
- This is demonstration code - not for clinical production use
