# AgentCore Deployment - Quick Reference

## Prerequisites Check

```powershell
cd backend
python test_agentcore_setup.py
```

## Deploy to AWS (3 commands)

```powershell
# 1. Install CLI (first time only)
pip install bedrock-agentcore-starter-toolkit

# 2. Deploy
.\deploy_agentcore.ps1

# 3. Test
agentcore invoke '{"prompt": "What is the datastore info?"}' --agent healthlake-agent
```

## Common Commands

```powershell
# Status
agentcore status --agent healthlake-agent --verbose

# Test locally first
.\deploy_agentcore.ps1 -LocalTest

# Update deployment
agentcore launch --agent healthlake-agent --auto-update-on-conflict

# View logs
aws logs tail /aws/lambda/healthlake-agent --follow --region us-west-2 --profile himssdemo

# Destroy
agentcore destroy --agent healthlake-agent
```

## Test Queries

```powershell
# Get datastore info
agentcore invoke '{"prompt": "What is the HealthLake datastore information?"}' --agent healthlake-agent

# Search patients
agentcore invoke '{"prompt": "Search for patients with diabetes"}' --agent healthlake-agent

# With session context
agentcore invoke '{
  "prompt": "List all conditions for patient 123",
  "session_id": "test-session",
  "context": {
    "user_id": "provider-001",
    "user_role": "provider",
    "active_member_id": "123"
  }
}' --agent healthlake-agent
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Module not found | Add to requirements.txt and redeploy |
| AWS auth failed | Set `$env:AWS_PROFILE = "himssdemo"` |
| VPC error | Verify subnets/security groups exist |
| Cold start slow | Use provisioned concurrency |

## Files Created

- `agent_agentcore.py` - AgentCore wrapper
- `deploy_agentcore.ps1` - Deployment script
- `test_agentcore_setup.py` - Pre-deployment checks
- `AGENTCORE_DEPLOYMENT.md` - Full guide
- `.bedrock_agentcore.yaml` - Config (created on first run)

## Architecture

```
User Request
    ↓
AgentCore Runtime (Lambda)
    ↓
agent_agentcore.py (wrapper)
    ↓
agent.py (Strands agent)
    ↓
AWS Services (HealthLake, Bedrock, S3)
```

## Cost Estimate

- **Free Tier**: 1M requests/month
- **After Free Tier**: ~$0.20 per 1M requests
- **Memory**: 512MB-2GB (auto-scaled)
- **Typical Cost**: $5-20/month for moderate usage

## Next Steps

1. ✓ Run `test_agentcore_setup.py`
2. ✓ Deploy with `.\deploy_agentcore.ps1`
3. ✓ Test with sample queries
4. ✓ Integrate with frontend
5. ✓ Monitor in CloudWatch

For detailed information, see `AGENTCORE_DEPLOYMENT.md`
