# Clinical Prior Auth — AgentCore

AgentCore-based implementation of the Clinical Prior Authorization agent.

## Overview

Automates healthcare prior authorization by analyzing patient FHIR data against billing guides and fee schedules to determine claim approval and cost calculations.

## Architecture

- **Runtime**: Amazon Bedrock AgentCore (`BedrockAgentCoreApp`)
- **Agent Framework**: Strands Agents SDK
- **Primary Model**: Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
- **Claim Calculation Model**: Claude Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`)

## Structure

```
agentcore/
├── pyproject.toml
├── src/
│   ├── main.py                    # AgentCore entrypoint
│   ├── model/load.py              # Model configuration
│   └── tools/prior_auth_tools.py  # Agent tools
├── test/
│   └── test_prior_auth.py         # Unit + integration tests
└── resources/
    └── hca_billing_guides_structured.json
```

## Setup

```bash
cd agentcore
pip install -e ".[dev]"
```

## Running Locally

```bash
cd src
python main.py
```

Then invoke with payload:
```json
{"patient_data": {"resourceType": "Bundle", "...": "..."}}
```

## Deploy to AgentCore

### Prerequisites

- AWS credentials configured with Bedrock and AgentCore access
- An IAM execution role for AgentCore (e.g., `AmazonBedrockAgentCore-us-east-1-*`)
- `agentcore` CLI installed (`pip install bedrock-agentcore-starter-toolkit`)

### Step 1: Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name clinical_prior_auth \
  --region us-east-1
```

### Step 2: Configure Agent

```bash
AWS_PROFILE=your-profile AWS_REGION=us-east-1 \
agentcore configure \
  --entrypoint src/main.py \
  --name clinical_prior_auth \
  --execution-role "arn:aws:iam::<ACCOUNT_ID>:role/AmazonBedrockAgentCore-us-east-1-<SUFFIX>" \
  --ecr <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/clinical_prior_auth \
  --disable-memory --disable-otel
```

When prompted:
- OAuth authorizer: **no**
- Request header allowlist: **no**

### Step 3: Deploy

```bash
agentcore deploy
```

This builds an ARM64 container via CodeBuild and deploys to AgentCore runtime (~3-5 min).

### Step 4: Invoke

```bash
agentcore invoke '{"patient_data": {"resourceType": "Bundle", "entry": [...]}}'
```

### Cleanup

```bash
agentcore destroy
aws ecr delete-repository --repository-name clinical_prior_auth --force --region us-east-1
```

## Testing

```bash
# Unit tests only
pytest test/ -m "not integration"

# All tests (requires AWS credentials with Bedrock access)
AWS_PROFILE=your-profile pytest test/ -v
```

## Tools

| Tool | Purpose |
|------|---------|
| `get_guidance_document_list` | Retrieve billing guide URLs for a specialty |
| `download_appropriate_document` | Download PDFs and fee schedules |
| `parse_pdf` | Extract text from billing guide PDFs |
| `parse_fee_schedule` | Parse Excel fee schedule into text |
| `calculate_claim_approval` | Determine approval/denial with cost breakdown |
