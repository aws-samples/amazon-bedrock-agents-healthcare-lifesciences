# UniProt Protein Search Agent — AgentCore

Protein database search via UniProt API. Based on [agentcore_template](../../../agentcore_template).

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
