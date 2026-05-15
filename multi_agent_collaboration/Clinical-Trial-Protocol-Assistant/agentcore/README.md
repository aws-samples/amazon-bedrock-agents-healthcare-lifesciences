# Clinical Trial Protocol Assistant — AgentCore

Multi-agent clinical trial protocol generation. Based on [agentcore_template](../../../agentcore_template).

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
