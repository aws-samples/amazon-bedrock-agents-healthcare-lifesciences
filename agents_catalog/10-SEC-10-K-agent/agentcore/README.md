# SEC 10-K Agent — AgentCore

SEC 10-K financial document search and analysis. Based on [agentcore_template](../../../agentcore_template).

## Deploy

```bash
# Option 1: Using deploy script (recommended)
pip install bedrock-agentcore-starter-toolkit click
python deploy.py

# Option 2: Using agentcore CLI directly
agentcore deploy
```

## Test

```bash
pytest tests/ -v
```
