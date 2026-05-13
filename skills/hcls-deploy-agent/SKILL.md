---
name: hcls-deploy-agent
description: Use when a developer wants to deploy an HCLS agent to Amazon Bedrock AgentCore, configure Gateway tools as MCP endpoints, set up authentication with Cognito, configure memory, or register an agent in the AgentCore Registry. Also use for deployment troubleshooting.
---

# Deploying an HCLS Agent

## When to use this skill

- Developer asks "how do I deploy this agent?"
- Developer needs to configure AgentCore Gateway, Runtime, Memory, or Identity
- Developer wants to expose tools as MCP endpoints
- Developer wants to register an agent in the AgentCore Registry

## Deployment Components

```
AgentCore Deployment
├── Runtime       — Hosts the agent container
├── Gateway       — Exposes tools as MCP endpoints (Lambda targets)
├── Memory        — Conversation persistence (semantic, summary, preferences)
├── Identity      — Cognito OAuth2 authentication
└── Registry      — Agent discovery for multi-agent workflows
```

## Steps

### 1. Prerequisites

```bash
# Install AgentCore CLI
pip install bedrock-agentcore

# Configure
agentcore configure --entrypoint main.py \
  -rf agent/requirements.txt \
  -er <IAM_ROLE_ARN> \
  --name <agent-name>
```

### 2. Deploy Infrastructure

Run the prerequisite script (creates Lambda tools, Cognito, Gateway):

```bash
./scripts/prereq.sh
```

This deploys CloudFormation stacks for:
- Lambda functions (tool handlers)
- IAM roles (agent execution, Gateway invocation)
- Cognito user pool (OAuth2 authentication)
- AgentCore Gateway (MCP endpoint with tool targets)
- AgentCore Memory (conversation persistence)

### 3. Deploy Agent Runtime

```bash
# Remove stale config
rm -f .agentcore.yaml

# Launch (builds container, pushes to ECR, deploys to Runtime)
agentcore launch
```

### 4. Verify

```bash
# Invoke the deployed agent
agentcore invoke '{"prompt": "Hello, can you help me?"}'

# Test Gateway tools independently
python tests/test_gateway.py --prompt "Test query"

# Test memory
python tests/test_memory.py load-conversation
```

### 5. Register in AgentCore Registry (optional)

For multi-agent discovery, register the agent:

```python
import boto3
client = boto3.client('bedrock-agentcore')

client.create_registry_record(
    registryName="hcls-registry",
    recordName="<agent-name>",
    description="<rich description for semantic search>",
    descriptorType="MCP",  # or "A2A" for agent-to-agent
    descriptors={...}
)
```

## Deployment Templates

| Template | What it deploys |
|----------|----------------|
| `agentcore_template/` | Backend: Runtime + Gateway + Memory + Streamlit UI |
| [FAST](https://github.com/awslabs/fullstack-solution-template-for-agentcore) | Full-stack: React/Amplify + Cognito + AgentCore + CDK |

## AWS MCP Servers Used

When deploying, the following AWS MCP servers help:
- `agentcore-docs` — API reference for Gateway/Runtime/Memory/Registry
- `aws-mcp` — create IAM roles, manage CloudFormation stacks, configure S3
- `strands-docs` — framework patterns for agent code

## References

- Deployment scripts: `agentcore_template/scripts/`
- Full deployment example: `agents_catalog/28-Research-agent-biomni-gateway-tools/scripts/prereq.sh`
- FAST template deployment: `agents_catalog/35-Terminology-agent/`
