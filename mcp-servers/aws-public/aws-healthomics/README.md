# AWS HealthOmics MCP Server

Local MCP server providing 60+ tools for managing AWS HealthOmics workflows, runs, sequence stores, and reference stores.

## Prerequisites

- AWS credentials configured (`aws configure`)
- [uv](https://astral.sh/uv) installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

Add to your assistant's MCP configuration:

```json
{
  "mcpServers": {
    "aws-healthomics": {
      "command": "uvx",
      "args": ["awslabs.aws-healthomics-mcp-server@latest"],
      "env": {
        "HEALTHOMICS_DEFAULT_MAX_RESULTS": "100"
      }
    }
  }
}
```

## Configuration

Create `.healthomics/config.toml` in your project:

```toml
omics_iam_role = "arn:aws:iam::<ACCOUNT_ID>:role/<HEALTHOMICS_ROLE_NAME>"
run_output_uri = "s3://<YOUR_BUCKET>/healthomics-outputs/"
run_storage_type = "DYNAMIC"
```

## Capabilities

- Workflow management (create, version, lint WDL/CWL/Nextflow)
- Run execution and monitoring
- Performance analysis and troubleshooting
- Batch run management
- Sequence and reference store management
- ECR container management for workflow containers
- Git integration via CodeConnections

## Steering Documents

The `steering/` folder contains SOP documents for common workflows. HCLS skills reference these for genomics-related tasks.

## Source

- Package: [awslabs.aws-healthomics-mcp-server](https://pypi.org/project/awslabs.aws-healthomics-mcp-server/)
- Setup guide: [sample-healthomics-agentic-setup](https://github.com/aws-samples/sample-healthomics-agentic-setup)
