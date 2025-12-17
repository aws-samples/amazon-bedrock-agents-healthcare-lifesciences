# Deep Research Agent

A Strands-based deep research agent for life sciences deployed to Amazon Bedrock AgentCore Runtime. This project includes two agent implementations: a single-agent version and a multi-agent collaborative version.

## Introduction

Artificial intelligence offers transformative opportunities to accelerate scientific research across multiple domains. AI can:

- Enhance scientific comprehension by understanding complex tables, figures, and text
- Support discovery through hypothesis generation and experimental planning
- Assist with drafting and revising manuscripts
- Facilitate peer review processes¹

Among these capabilities, the "survey" function—finding related work and generating comprehensive summary reports—represents a critical bottleneck in research workflows that AI agents can effectively address¹.

Deep research agents represent a specialized class of AI systems designed to autonomously conduct complex research tasks by planning research strategies, gathering information from diverse sources, analyzing findings, and synthesizing comprehensive reports with proper citations. Unlike general AI assistants that simply answer questions or single-function research tools that address isolated tasks, deep research agents provide end-to-end research orchestration with autonomous workflow capabilities, specialized research tools, and integrated reasoning across multiple research functions². These systems can conduct multi-step research that accomplishes in minutes what would take researchers many hours, leveraging advanced planning methodologies and sophisticated tool integration frameworks to handle complex tasks requiring multi-step reasoning³.

For scientific literature survey tasks, deep research agents excel because they can maintain context across multiple research phases, adapt their search strategies based on discovered information, and synthesize findings from hundreds of sources into coherent, well-cited reports. Their ability to autonomously plan research approaches, interact with domain-specific databases like PubMed Central, and apply advanced retrieval augmented generation techniques makes them particularly well-suited for navigating the vast and rapidly expanding scientific literature landscape.

Sources

1. Chen, Qiguang, et al. "AI4Research: A Survey of Artificial Intelligence for Scientific Research." arXiv, 5 Aug. 2025, doi.org/10.48550/arXiv.2507.01903 .
1. Xu, Renjun, and Jingwen Peng. "A Comprehensive Survey of Deep Research: Systems, Methodologies, and Applications." arXiv, 14 June 2025, doi:10.48550/arXiv.2506.12594 .
1. Engineering at Anthropic: How we built our multi-agent research system

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- AWS CLI configured with appropriate credentials
- Access to Amazon Bedrock AgentCore

## Project Structure

```bash
.
├── agents/
│   ├── dr-agent/          # Single agent implementation
│   └── dr-multi-agent/    # Multi-agent collaborative implementation
├── infrastructure/
│   ├── root.yaml          # Root CloudFormation stack
│   ├── dr-agent.yaml      # Single agent infrastructure
│   ├── dr-multi-agent.yaml # Multi-agent infrastructure
│   └── container.yaml     # Container build configuration
├── scripts/
│   ├── deploy.sh          # Deployment script
│   └── destroy.sh         # Stack teardown script
├── invoke_agentcore.py    # CLI tool for invoking the agent
└── pyproject.toml         # Python project configuration
```

## Deployment

### Setup

First, sync the Python environment:

```bash
uv sync
```

### Deploy to AgentCore

Deploy the agent to AgentCore Runtime using the deployment script:

```bash
./scripts/deploy.sh <project-name> <s3-bucket-name>
```

**Parameters:**

- `<project-name>` - CloudFormation stack name and project identifier (e.g., `research-agent`)
- `<s3-bucket-name>` - S3 bucket name for deployment artifacts and agent code

**Example:**

```bash
./scripts/deploy.sh research-agent my-deployment-bucket
```

The deployment script will:

1. Validate CloudFormation templates
2. Package and upload agent code to S3
3. Deploy the CloudFormation stack with all resources
4. Build container images via CodeBuild
5. Create AgentCore runtime(s)

After deployment completes, the stack outputs will show the agent runtime name(s) you'll use for invocation.

### Teardown

To remove all deployed resources:

```bash
./scripts/destroy.sh <project-name>  <s3-bucket-name>
```

## Invocation

### Using the Python CLI Tool

The `invoke_agentcore.py` script provides a convenient way to interact with your deployed agent. It automatically looks up the agent by name and streams responses to stdout.

#### Basic Usage

```bash
uv run invoke_agentcore.py \
  --name <agent-runtime-name> \
  --prompt "Tell me about yourself"
```

Replace `<agent-runtime-name>` with the actual runtime name from your deployment outputs.

#### With Session ID (for conversation continuity)

```bash
# Generate a session ID and reuse it for multiple turns
SESSION_ID=$(uuidgen)

# First message
uv run invoke_agentcore.py \
  --name <agent-runtime-name> \
  --session-id $SESSION_ID \
  --prompt "My name is Alice"

# Follow-up message (maintains context)
uv run invoke_agentcore.py \
  --name <agent-runtime-name> \
  --session-id $SESSION_ID \
  --prompt "What is my name?"
```

#### With Specific Region

```bash
uv run invoke_agentcore.py \
  --name <agent-runtime-name> \
  --region us-east-1 \
  --prompt "What can you help me with?"
```

#### Pipe Input

```bash
echo "Tell me about yourself" | uv run invoke_agentcore.py --name <agent-runtime-name>
```

### Using AWS CLI

You can also invoke the agent directly using the AWS CLI:

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn <agent-runtime-arn> \
  --qualifier DEFAULT \
  --runtime-session-id $(uuidgen) \
  --payload "$(echo -n '{"prompt":"Tell me about yourself"}' | base64)" \
  --region us-east-1 \
  response.json
```

Get the `<agent-runtime-arn>` from your CloudFormation stack outputs.

## CLI Options

```bash
uv run invoke_agentcore.py --help
```

**Available options:**

- `--name` (required) - Name of the deployed agent runtime
- `--prompt` - Prompt to send to the agent (or pipe from stdin)
- `--session-id` - Session ID for conversation continuity (auto-generated if not provided)
- `--region` - AWS region name (uses default if not provided)

## Agent Implementations

### Single Agent (dr-agent)

A standalone research agent that can search PubMed Central and gather evidence for life sciences research queries.

**Key features:**

- PubMed Central search integration
- Evidence gathering and synthesis
- Containerized deployment

### Multi-Agent (dr-multi-agent)

A collaborative multi-agent system with specialized roles for comprehensive research tasks.

**Key features:**

- Lead agent for orchestration
- Specialized PMC research agent
- DynamoDB-backed evidence storage
- Report generation capabilities
- Enhanced collaboration between agents

## Development

### Install Dependencies

```bash
uv sync
```

### Local Testing

Test the agent logic locally before deployment by running the agent code directly or using Python notebooks for interactive development.

## Troubleshooting

### Agent Not Found

If you get "Agent not found" error when invoking:

1. Verify the agent runtime name matches the deployed name (check CloudFormation stack outputs)
2. Ensure you're using the correct AWS region
3. Confirm your AWS credentials have permission to access AgentCore
4. Check that the deployment completed successfully

### Deployment Failures

If deployment fails:

1. Verify the S3 bucket exists and you have write permissions
2. Check that you have the required IAM permissions for CloudFormation, CodeBuild, ECR, and AgentCore
3. Review CloudFormation events in the AWS Console for specific error messages
4. Ensure the bucket is in the same region as your deployment

### Session Context Not Maintained

Ensure you're using the same `--session-id` for all messages in a conversation.

### Timeout Errors

For long-running research operations, the invocation script is configured with a 900-second read timeout. If you still encounter timeouts, check your agent's processing logic or increase the timeout in `invoke_agentcore.py`.

## License

See the main repository LICENSE file.
