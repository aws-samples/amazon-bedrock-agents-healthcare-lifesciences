# Enrollment Pulse — AgentCore

Clinical trial enrollment optimization agent. Based on [agentcore_template](../../../agentcore_template).

## Structure
```
main.py                    # AgentCore entrypoint
agent/
├── agent_config/
│   ├── agent.py           # Agent task + model config
│   ├── tools.py           # Clinical operations tools
│   ├── epidemiology_tools.py
│   ├── clinical_trials_tools.py
│   └── live_clinical_trials_tools.py
├── data/                  # Processors + CSV data
└── analysis/              # Enrollment metrics
tests/test_agent.py
```

## Deploy
```bash
aws ecr create-repository --repository-name enrollment_pulse --region us-east-1
agentcore configure --entrypoint main.py --name enrollment_pulse \
  --ecr <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/enrollment_pulse \
  --execution-role <ROLE_ARN> --disable-memory --disable-otel
agentcore deploy
agentcore invoke '{"prompt": "What is the current enrollment status by site?"}'
```

## Deploy (alternative)

```bash
pip install bedrock-agentcore-starter-toolkit click
python deploy.py
```
