# Research Agent

A Strands-based deep research agent for life science deployed to Amazon Bedrock AgentCore Runtime.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- AWS CLI configured with appropriate credentials
- Access to Amazon Bedrock AgentCore

## Project Structure

```bash
.
├── agents/
│   └── dr-agent/          # Agent implementation
├── infrastructure/
│   └── root.yaml          # CloudFormation/CDK infrastructure
├── scripts/
│   └── deploy.sh          # Deployment script
└── invoke_agentcore.py    # CLI tool for invoking the agent
```

## Deployment

Deploy the agent to AgentCore Runtime using the deployment script:

```bash
./scripts/deploy.sh my-project my-bucket
```

**Parameters:**

- `my-project` - Agent identifier
- `my-bucket` - S3 bucket name for deployment artifacts

The deployment will output a Runtime ID (e.g., `dr_agent-abcdefg`) that you'll use for invocation.

## Invocation

### Using the Python CLI Tool

The `invoke_agentcore.py` script provides a convenient way to interact with your deployed agent.

#### Basic Usage

```bash
uv run invoke_agentcore.py \
  --name dr_agent \
  --prompt "Tell me about yourself"
```

#### With Session ID (for conversation continuity)

```bash
# Generate a session ID and reuse it for multiple turns
SESSION_ID=$(uuidgen)

# First message
uv run invoke_agentcore.py \
  --name dr_agent \
  --session-id $SESSION_ID \
  --prompt "My name is Alice"

# Follow-up message (maintains context)
uv run invoke_agentcore.py \
  --name dr_agent \
  --session-id $SESSION_ID \
  --prompt "What is my name?"
```

#### With Specific Region

```bash
uv run invoke_agentcore.py \
  --name dr_agent \
  --region us-east-1 \
  --prompt "What can you help me with?"
```

#### Pipe Input

```bash
echo "Tell me about yourself" | uv run invoke_agentcore.py --name dr_agent
```

### Using AgentCore CLI

```bash
agentcore invoke dr_agent-abcdefg --prompt "What can you help me with?"
```

For interactive mode:

```bash
agentcore invoke dr_agent-abcdefg --interactive
```

### Using AWS CLI

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn arn:aws:bedrock-agentcore:us-east-1:123456789:runtime/dr_agent-abcdefg \
  --qualifier DEFAULT \
  --runtime-session-id $(uuidgen) \
  --payload "$(echo -n '{"prompt":"Tell me about yourself"}' | base64)" \
  --region us-east-1 \
  response.json
```

## CLI Options

```bash
uv run invoke_agentcore.py --help
```

**Available options:**

- `--name` (required) - Name of the deployed agent runtime
- `--prompt` - Prompt to send to the agent (or pipe from stdin)
- `--session-id` - Session ID for conversation continuity (auto-generated if not provided)
- `--region` - AWS region name (uses default if not provided)

## Development

### Install Dependencies

```bash
uv sync
```

### Run Tests

```bash
uv run pytest
```

### Local Development

For local testing before deployment, use the AgentCore dev server:

```bash
agentcore dev
```

Then invoke locally:

```bash
agentcore invoke --local --prompt "Test prompt"
```

## Troubleshooting

### Agent Not Found

If you get "Agent not found" error, verify:

1. The agent name matches the deployed runtime name
2. You're using the correct AWS region
3. Your AWS credentials have permission to access AgentCore

### Session Context Not Maintained

Ensure you're using the same `--session-id` for all messages in a conversation.

### Timeout Errors

For long-running operations, the script is configured with a 900-second read timeout. If you still encounter timeouts, check your agent's processing logic.

## License

See the main repository LICENSE file.
