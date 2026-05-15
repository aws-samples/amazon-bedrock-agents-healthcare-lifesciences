# Single Cell QC Agent — AgentCore

Single-cell RNA sequencing quality control. Based on [agentcore_template](../../../agentcore_template).

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
