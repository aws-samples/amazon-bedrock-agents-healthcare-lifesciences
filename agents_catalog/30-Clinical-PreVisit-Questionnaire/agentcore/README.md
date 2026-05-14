# Clinical PreVisit Questionnaire — AgentCore

UCLA Health Pre-Visit Questionnaire agent. Based on [agentcore_template](../../../agentcore_template).

## Deploy
```bash
aws ecr create-repository --repository-name clinical_pvq --region us-east-1
agentcore configure --entrypoint main.py --name clinical_pvq \
  --ecr <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/clinical_pvq \
  --execution-role <ROLE_ARN> --disable-memory --disable-otel
agentcore deploy
agentcore invoke '{"message": "I need to fill out my pre-visit form"}'
```
