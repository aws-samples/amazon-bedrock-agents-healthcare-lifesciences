# ICH Guidelines — Bedrock Knowledge Base Setup

ICH guideline search uses the existing [awslabs Bedrock KB Retrieval MCP Server](https://github.com/awslabs/mcp/tree/main/src/bedrock-kb-retrieval-mcp-server) rather than a custom Lambda deployment. This directory provides the data and setup instructions.

## Tools Available (via awslabs.bedrock-kb-retrieval-mcp-server)

| Tool | What it does |
|------|-------------|
| `retrieve` | Search ICH guidelines for regulatory guidance on clinical trial design and conduct |

### Example Queries

- "How should protocol objectives be stated per ICH E6?"
- "Randomization requirements for Phase 2 trials"
- "Statistical principles for sample size justification"
- "General considerations for study design per E8"

## Architecture

```
Client (Claude Code / Kiro / Amazon Quick)
    |
    | Local MCP (stdio)
    v
awslabs.bedrock-kb-retrieval-mcp-server (uvx)
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

The `data/` directory contains these PDFs for the Knowledge Base.

## Setup

### Step 1: Create the Knowledge Base

1. Create an S3 bucket and upload the ICH PDFs:
   ```bash
   BUCKET="ich-guidelines-${AWS_ACCOUNT_ID}-${AWS_REGION}"
   aws s3 mb s3://$BUCKET
   aws s3 cp data/ s3://$BUCKET/ --recursive --exclude "README.md"
   ```

2. Create a Bedrock Knowledge Base via the console or CLI:
   - Data source: the S3 bucket above
   - Embedding model: Amazon Titan Embeddings v2
   - Vector store: OpenSearch Serverless (auto-created)
   - Chunking: 300 tokens, 20% overlap

3. Sync the data source after creation (~2-5 minutes)

4. Note the Knowledge Base ID for the next step

### Step 2: Configure the MCP Server

Add to your MCP client configuration:

#### Kiro (`~/.kiro/settings/mcp.json`)

```json
{
  "mcpServers": {
    "awslabs.bedrock-kb-retrieval-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.bedrock-kb-retrieval-mcp-server@latest"],
      "env": {
        "KNOWLEDGE_BASE_ID": "<YOUR_KB_ID>",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

#### Claude Code

```bash
claude mcp add awslabs.bedrock-kb-retrieval-mcp-server \
  -- uvx awslabs.bedrock-kb-retrieval-mcp-server@latest
```

Set `KNOWLEDGE_BASE_ID` in your environment before launching.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| `uvx` | [Install uv](https://docs.astral.sh/uv/getting-started/installation/) |
| AWS credentials | `bedrock:Retrieve` permission on the KB |
| Bedrock KB | Created per Step 1 above |
| Region | `us-east-1` or `us-west-2` (Bedrock KB availability) |

## Why Not a Custom Gateway?

The existing `awslabs.bedrock-kb-retrieval-mcp-server` already provides Bedrock KB retrieval as an MCP tool. Using it avoids maintaining a separate Lambda, Cognito stack, and AgentCore Gateway registration for what is a standard retrieve operation. The fda-ecfr server still needs a custom gateway because it wraps a public REST API with custom parsing logic.

## Cleanup

```bash
# Delete the S3 bucket
aws s3 rb s3://ich-guidelines-${AWS_ACCOUNT_ID}-${AWS_REGION} --force

# Delete the Knowledge Base via console or CLI
aws bedrock-agent delete-knowledge-base --knowledge-base-id <YOUR_KB_ID>
```

## Source

- ICH Guidelines: [ICH.org](https://www.ich.org/page/quality-guidelines)
- FDA hosted PDFs: [FDA.gov ICH Guidance](https://www.fda.gov/science-research/clinical-trials-and-human-subject-protection/ich-guidance-documents)
