# AgentCore Migration — Process & Metrics

## Overview

Migration of HCLS agents from standalone Strands SDK / CFN Bedrock Agents to the standardized AgentCore runtime pattern, performed using **Kiro CLI** as the AI development agent.

## Phase 1 Results

| Agent | Time (min) | Tools | Tests | Deploy Verified |
|-------|-----------|-------|-------|-----------------|
| 29 - Clinical Prior Auth | ~45 | 5 | 7 | ✅ |
| 27 - Enrollment Pulse | ~30 | 40+ | 7 | ✅ |
| 30 - Clinical PreVisit Questionnaire | ~25 | 12 | 6 | ✅ |
| 26 - Medical Device | ~15 | 4 | 5 | ✅ |

**Average: ~29 min per agent** (including deploy + live verification)

Note: Agent 29 took longest as the first migration — established the pattern, discovered container packaging issues, and identified that Amazon Titan Text Express is EOL. Subsequent agents were faster as the pattern was reused.

## Template Used

**agentcore_template** (Template 1) — [source](../../agentcore_template)

Reference implementation: [Agent 28 - Research Agent](../../agents_catalog/28-Research-agent-biomni-gateway-tools)

### Standardized Structure

```
agentcore/
├── main.py                          # BedrockAgentCoreApp entrypoint
├── agent/
│   ├── agent_config/
│   │   ├── agent.py                 # Agent task, model config, system prompt
│   │   └── tools/                   # @tool decorated functions
│   ├── data/ or resources/          # Data files (if needed)
│   └── ...
├── tests/
│   └── test_agent.py               # Automated pytest suite
└── pyproject.toml
```

## Requirements Provided to Kiro

1. **Issue #248** (Epic) — Migrate all agents to AgentCore runtime
2. **Template reference** — `agentcore_template/` and Agent 28 as canonical patterns
3. **Acceptance criteria per agent:**
   - Agent runs on AgentCore runtime with Strands SDK
   - Passes linting: ruff, bandit (security)
   - Deployed and tested in AWS account with live invocations
   - README updated with deployment instructions
   - All tests automated (no manual steps)

## Test Framework

All tests are fully automated via `pytest`. No manual intervention required.

```bash
# Run all unit tests (no AWS needed)
pytest tests/ -m "not integration"

# Run integration tests (requires AWS credentials + Bedrock access)
AWS_PROFILE=your-profile pytest tests/ -m "integration"

# Run everything
AWS_PROFILE=your-profile pytest tests/ -v
```

### Test Categories

| Category | What it tests | AWS Required |
|----------|--------------|--------------|
| Data/Model loading | CSV processors, data models initialize correctly | No |
| Tool execution | Tools return expected output format with test data | No |
| Model config | Model IDs are current (not deprecated) | No |
| Live invocation | Agent responds via Bedrock API | Yes |
| AgentCore deploy | Full end-to-end on AgentCore runtime | Yes (manual) |

### Linting & Security

| Tool | Purpose | Automated |
|------|---------|-----------|
| ruff | Python linting (style, unused imports, errors) | ✅ `ruff check .` |
| bandit | Security scanning (hardcoded secrets, injection, etc.) | ✅ `bandit -r agent/` |
| cfn-lint | CloudFormation template validation | ✅ (if CFN present) |

## Key Findings During Migration

1. **Amazon Titan Text Express is EOL** — Replaced with Claude Haiku 4.5 for cost-sensitive tasks
2. **Container data packaging** — Data files must be co-located with Python modules (not at project root) for AgentCore container builds
3. **ECR configuration** — Must use full URI (`<account>.dkr.ecr.<region>.amazonaws.com/<repo>`) in `agentcore configure`
4. **Model compatibility** — Claude Sonnet 4.5 does not allow `temperature` + `top_p` simultaneously
5. **Import patterns** — Replace `sys.path.append` hacks with absolute imports when code is on sys.path

## Kiro CLI Usage

- **MCP Servers**: AWS documentation, CloudWatch, ECS (built-in)
- **Steering files**: None custom — used existing repo templates as reference
- **Key capabilities used**: File read/write, shell execution, grep/glob search, AWS CLI, GitHub CLI (`gh`)
- **Workflow**: Read existing code → understand pattern → create AgentCore structure → port tools → fix imports → write tests → lint → deploy → verify

## Deployed Agents (Sandbox)

| Agent | ARN |
|-------|-----|
| clinical_prior_auth | `arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT_ID>:runtime/clinical_prior_auth-0I0JTA3PT0` |
| enrollment_pulse | `arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT_ID>:runtime/enrollment_pulse-6YHCrd3h6H` |
| clinical_pvq | `arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT_ID>:runtime/clinical_pvq-F5sm875N80` |
| medical_device_agent | `arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT_ID>:runtime/medical_device_agent-YiCRKk2g4F` |
