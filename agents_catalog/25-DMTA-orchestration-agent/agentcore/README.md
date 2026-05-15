# DMTA Orchestration Agent — AgentCore

Design-Make-Test-Analyze cycle orchestration. Based on [agentcore_template](../../../agentcore_template).

## Deploy

```bash
# Option 1: Using deploy script (recommended)
npm install -g @aws/agentcore  # if not already installed
python deploy.py              # or: agentcore deploy -y

# Option 2: Using agentcore CLI directly
agentcore deploy
```

## Test

```bash
pytest tests/ -v
```
