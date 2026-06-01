# ICH Guidelines MCP Server — AgentCore Gateway

Semantic search over ICH guideline documents (E6, E8, E9) using Amazon Bedrock Knowledge Bases, deployed as a Lambda target behind AgentCore Gateway.

## Tools Available

| Tool | What it does |
|------|-------------|
| `search_ich_guidance` | Search ICH guidelines for regulatory guidance on clinical trial design and conduct |

### Example Queries

- "How should protocol objectives be stated per ICH E6?"
- "Randomization requirements for Phase 2 trials"
- "Statistical principles for sample size justification"
- "General considerations for study design per E8"

## Architecture

```
Client (Claude Code / Kiro / Amazon Quick)
    |
    | HTTPS + JWT token
    v
AgentCore Gateway (MCP protocol)
    |
    | Lambda invocation
    v
ich-guidelines Lambda (Python)
    |
    | Bedrock Retrieve API
    v
Bedrock Knowledge Base
    |
    v
OpenSearch Serverless (vector index)
    |
    v
S3 Bucket (ICH PDF documents)
```

## Data Sources

All documents are publicly downloadable from the FDA website:
https://www.fda.gov/science-research/clinical-trials-and-human-subject-protection/ich-guidance-documents

| Guideline | Title |
|-----------|-------|
| ICH E6(R2) | Good Clinical Practice, Integrated Addendum |
| ICH E8(R1) | General Considerations for Clinical Studies |
| ICH E9 | Statistical Principles for Clinical Trials |

The `data/` directory contains these PDFs for local development. Production deployments sync from S3.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| AWS CLI | Configured with appropriate credentials |
| @aws/agentcore CLI | `npm install -g @aws/agentcore` |
| Python 3.12+ | For Lambda runtime |
| AWS Account | Permissions: CloudFormation, Lambda, IAM, Bedrock, OpenSearch Serverless, S3 |
| Region | `us-east-1` or `us-west-2` (Bedrock KB + AgentCore availability) |

## Deployment

### Quick Start

```bash
cd mcp-servers/agentcore-gateway/ich-guidelines
./deploy.sh
```

### What the Deploy Script Does

1. Creates S3 bucket and uploads ICH PDFs from `data/`
2. Deploys Bedrock Knowledge Base with OpenSearch Serverless vector store
3. Syncs the data source (indexes PDFs)
4. Deploys Lambda function with KB_ID environment variable
5. Deploys Cognito authentication stack
6. Registers Lambda as AgentCore Gateway target
7. Stores endpoint URL and KB ID in SSM Parameter Store

### SSM Parameters Created

| Parameter | Description |
|-----------|-------------|
| `/app/ich-guidelines/agentcore/mcp_url` | MCP endpoint URL |
| `/app/ich-guidelines/kb_id` | Bedrock Knowledge Base ID |
| `/app/ich-guidelines/bucket_name` | S3 bucket with ICH PDFs |
| `/app/ich-guidelines/agentcore/machine_client_id` | Cognito client ID |
| `/app/ich-guidelines/agentcore/cognito_secret` | Cognito client secret |

## Connecting to Your AI Assistant

### Step 1: Get an access token

```bash
source get-token.sh
# Sets: ICH_MCP_TOKEN, ICH_MCP_URL
```

### Step 2: Connect

#### Claude Code

```bash
claude mcp add --transport http \
  --header "Authorization: Bearer $ICH_MCP_TOKEN" \
  ich-guidelines "$ICH_MCP_URL"
```

#### Kiro

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "ich-guidelines": {
      "transportType": "http",
      "url": "<ICH_MCP_URL>",
      "headers": {
        "Authorization": "Bearer ${ICH_MCP_TOKEN}"
      }
    }
  }
}
```

## Local Development

For local testing without deploying the full Knowledge Base:

```bash
pip install -r requirements.txt
# Use a local vector store (FAISS/ChromaDB) with the PDFs in data/
```

The `data/README.md` documents the PDF sources and licensing.

## Limitations

- ICH guidelines are static documents (updated infrequently by ICH)
- No real-time API available from ICH.org
- Knowledge Base requires initial sync after PDF upload (~2-5 minutes)
- Retrieval quality depends on chunking strategy (default: 300 tokens, 20% overlap)

## Cleanup

```bash
aws cloudformation delete-stack --stack-name ich-guidelines-lambda
aws cloudformation delete-stack --stack-name ich-guidelines-cognito
aws cloudformation delete-stack --stack-name ich-guidelines-kb
aws s3 rb s3://ich-guidelines-${AWS_ACCOUNT_ID}-${AWS_REGION} --force
aws ssm delete-parameters --names \
  "/app/ich-guidelines/agentcore/mcp_url" \
  "/app/ich-guidelines/kb_id" \
  "/app/ich-guidelines/bucket_name" \
  "/app/ich-guidelines/agentcore/machine_client_id" \
  "/app/ich-guidelines/agentcore/cognito_secret"
```

## Source

- ICH Guidelines: [ICH.org](https://www.ich.org/page/quality-guidelines)
- FDA hosted PDFs: [FDA.gov ICH Guidance](https://www.fda.gov/science-research/clinical-trials-and-human-subject-protection/ich-guidance-documents)
