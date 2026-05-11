# Clinical Prior Authorization Agent — AgentCore

Automates healthcare prior authorization by analyzing patient FHIR data against billing guides and fee schedules.

## Architecture

Based on the [agentcore_template](../../../agentcore_template) pattern.

- **Runtime**: Amazon Bedrock AgentCore (`BedrockAgentCoreApp`)
- **Primary Model**: Claude Sonnet 4.5
- **Claim Calculation Model**: Claude Haiku 4.5
- **Tools**: Document retrieval, PDF parsing, fee schedule analysis, claim approval

## Structure

```
agentcore/
├── main.py                          # AgentCore entrypoint
├── agent/
│   ├── agent_config/
│   │   └── agent.py                 # Agent creation, tools, and task logic
│   └── resources/
│       └── hca_billing_guides_structured.json
├── tests/
│   └── test_agent.py
└── pyproject.toml
```

## Setup & Test

```bash
pip install -e ".[dev]"
pytest tests/ -m "not integration"

# With AWS credentials:
AWS_PROFILE=your-profile pytest tests/ -v
```

## Deploy to AgentCore

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name clinical_prior_auth --region us-east-1

# 2. Configure
agentcore configure \
  --entrypoint main.py \
  --name clinical_prior_auth \
  --execution-role <ROLE_ARN> \
  --ecr <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/clinical_prior_auth \
  --disable-memory --disable-otel

# 3. Deploy
agentcore deploy

# 4. Invoke
agentcore invoke '{"prompt": "Patient with knee pain requiring orthopedic consultation"}'
```

## Cleanup

```bash
agentcore destroy
aws ecr delete-repository --repository-name clinical_prior_auth --force --region us-east-1
```
