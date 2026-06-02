# Medical Device Coordinator — AgentCore

Medical device monitoring, PubMed research, and clinical trials lookup. Based on [agentcore_template](../../../agentcore_template).

## Deploy
```bash
aws ecr create-repository --repository-name medical_device_agent --region us-east-1
agentcore configure --entrypoint main.py --name medical_device_agent \
  --ecr <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/medical_device_agent \
  --execution-role <ROLE_ARN> --disable-memory --disable-otel
agentcore deploy
agentcore invoke '{"prompt": "List all medical devices and their status"}'
```

## Deploy (alternative)

```bash
npm install -g @aws/agentcore  # if not already installed
python deploy.py              # or: agentcore deploy -y
```
