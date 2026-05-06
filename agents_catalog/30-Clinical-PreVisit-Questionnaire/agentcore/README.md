# Clinical PreVisit Questionnaire — AgentCore

AgentCore-based implementation of the UCLA Health Pre-Visit Questionnaire agent.

## Overview

Conversational AI agent that helps patients complete health questionnaires before their visit. Supports two modes: standard (Sonnet 4.5) and fast (Haiku 4.5).

## Architecture

- **Runtime**: Amazon Bedrock AgentCore (`BedrockAgentCoreApp`)
- **Agent Framework**: Strands Agents SDK
- **Models**: Claude Sonnet 4.5 (standard) / Claude Haiku 4.5 (fast mode)
- **Tools**: Class-based tools for data collection (basic info, medical history, medications, social history, symptoms, health maintenance)

## Structure

```
agentcore/
├── pyproject.toml
├── src/
│   ├── main.py                    # AgentCore entrypoint
│   ├── model/load.py              # Model configuration (Sonnet + Haiku)
│   ├── agents/
│   │   ├── pvq_agent.py           # Standard agent (Sonnet 4.5)
│   │   ├── pvq_agent_fast.py      # Fast agent (Haiku 4.5)
│   │   └── tools/                 # Tool modules (6 categories)
│   ├── models/patient_data.py     # Pydantic data models
│   └── utils/
│       ├── pdf_generator.py       # PDF form generation
│       └── validators.py          # Input validation
└── test/
    └── test_pvq.py
```

## Setup

```bash
cd agentcore
pip install -e ".[dev]"
```

## Testing

```bash
# Unit tests
pytest test/ -m "not integration"

# All tests (requires AWS credentials)
AWS_PROFILE=your-profile pytest test/ -v
```

## Deploy to AgentCore

```bash
# Create ECR repo
aws ecr create-repository --repository-name clinical_pvq --region us-east-1

# Configure
AWS_PROFILE=your-profile AWS_REGION=us-east-1 \
agentcore configure \
  --entrypoint src/main.py \
  --name clinical_pvq \
  --execution-role "arn:aws:iam::<ACCOUNT_ID>:role/AmazonBedrockAgentCore-us-east-1-<SUFFIX>" \
  --ecr <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/clinical_pvq \
  --disable-memory --disable-otel

# Deploy
agentcore deploy

# Invoke (standard mode)
agentcore invoke '{"message": "I need to fill out my pre-visit form. I have a headache."}'

# Invoke (fast mode)
agentcore invoke '{"message": "I have diabetes and take metformin", "mode": "fast"}'
```

## Cleanup

```bash
agentcore destroy
aws ecr delete-repository --repository-name clinical_pvq --force --region us-east-1
```
