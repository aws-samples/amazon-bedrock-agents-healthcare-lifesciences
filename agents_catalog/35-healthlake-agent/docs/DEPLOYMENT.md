# HealthLake Agent - AgentCore Deployment Guide

This guide covers deploying the HealthLake Agent to AWS Bedrock AgentCore Runtime.

## Architecture

```
AgentCore Runtime (Serverless)
    ↓
Lambda Function (agent_agentcore.py)
    ↓
Strands Agent (agent.py)
    ↓
AWS Services (HealthLake, Bedrock, S3)
```

## Prerequisites

1. **AWS CLI configured** with profile: `himssdemo`
2. **Python 3.12+** installed
3. **AgentCore CLI** (will be installed automatically)
4. **AWS Permissions** for:
   - Lambda (create functions)
   - IAM (create roles)
   - CloudWatch Logs
   - HealthLake, Bedrock, S3 access

## Quick Start

### Option 1: Using PowerShell Script (Recommended)

```powershell
cd backend

# Deploy to AWS
.\deploy_agentcore.ps1 -AgentName "healthlake-agent" -Region "us-west-2"

# Test locally first
.\deploy_agentcore.ps1 -AgentName "healthlake-agent" -LocalTest

# Verbose output
.\deploy_agentcore.ps1 -AgentName "healthlake-agent" -Verbose
```

### Option 2: Manual CLI Commands

```powershell
cd backend

# 1. Install AgentCore CLI
pip install bedrock-agentcore-starter-toolkit

# 2. Configure agent
agentcore configure `
  --entrypoint agent_agentcore.py `
  --name healthlake-agent `
  --region us-west-2 `
  --runtime PYTHON_3_12 `
  --requirements-file requirements.txt `
  --deployment-type direct_code_deploy `
  --vpc `
  --subnets subnet-026c3f14dfe982db4,subnet-03eb3c4ca581fbfa9 `
  --security-groups sg-029ee008aec2e8a6e `
  --non-interactive

# 3. Deploy to AWS
agentcore launch --agent healthlake-agent --auto-update-on-conflict

# 4. Check status
agentcore status --agent healthlake-agent --verbose

# 5. Test the agent
agentcore invoke '{"prompt": "What is the HealthLake datastore information?"}' --agent healthlake-agent
```

## Configuration Details

### VPC Configuration

The agent is deployed in VPC mode to access HealthLake privately:

- **Subnets**: `subnet-026c3f14dfe982db4`, `subnet-03eb3c4ca581fbfa9`
- **Security Group**: `sg-029ee008aec2e8a6e`
- **VPC**: `vpc-0847ef8e50f8e3cc2`

### Runtime Configuration

- **Python Version**: 3.12
- **Deployment Type**: `direct_code_deploy` (no Docker required)
- **Architecture**: ARM64 (handled automatically)
- **Region**: us-west-2

### Environment Variables

AgentCore automatically passes these from your local environment:

- `AWS_REGION`
- `HEALTHLAKE_DATASTORE_ID`
- `BEDROCK_MODEL_ID`
- `BEDROCK_REGION`

To add custom environment variables during deployment:

```powershell
agentcore launch --agent healthlake-agent --env "LOG_LEVEL=DEBUG" --env "CUSTOM_VAR=value"
```

## Testing

### Test Locally

```powershell
# Start local server
agentcore launch --agent healthlake-agent --local

# In another terminal, test
agentcore invoke '{"prompt": "List FHIR resources"}' --agent healthlake-agent --local
```

### Test Deployed Agent

```powershell
# Simple query
agentcore invoke '{"prompt": "What is the datastore info?"}' --agent healthlake-agent

# With session context
agentcore invoke '{
  "prompt": "Search for patients",
  "session_id": "test-session-123",
  "context": {
    "user_id": "provider-001",
    "user_role": "provider",
    "active_member_id": null
  }
}' --agent healthlake-agent

# With custom headers
agentcore invoke '{"prompt": "Hello"}' --agent healthlake-agent --headers "X-Custom-Header:value"
```

## Monitoring

### Check Agent Status

```powershell
# Basic status
agentcore status --agent healthlake-agent

# Detailed status with configuration
agentcore status --agent healthlake-agent --verbose
```

### View Logs

AgentCore automatically creates CloudWatch Log Groups:

```powershell
# View logs in AWS Console
# Log Group: /aws/lambda/healthlake-agent-*

# Or use AWS CLI
aws logs tail /aws/lambda/healthlake-agent --follow --region us-west-2 --profile himssdemo
```

### Session Management

```powershell
# Stop a specific session
agentcore stop-session --session-id "session-123" --agent healthlake-agent

# Stop all sessions
agentcore stop-session --agent healthlake-agent
```

## Updating the Agent

### Update Code

```powershell
# Make changes to agent.py or agent_agentcore.py

# Redeploy (automatically updates existing deployment)
agentcore launch --agent healthlake-agent --auto-update-on-conflict
```

### Update Configuration

```powershell
# Reconfigure
agentcore configure --entrypoint agent_agentcore.py --name healthlake-agent --non-interactive

# Deploy changes
agentcore launch --agent healthlake-agent
```

## Integration with Frontend

### API Endpoint

After deployment, AgentCore provides an endpoint:

```
https://<agent-id>.execute-api.us-west-2.amazonaws.com/prod/invoke
```

Get the endpoint URL:

```powershell
agentcore status --agent healthlake-agent --verbose
```

### Frontend Integration

Update your frontend to call the AgentCore endpoint:

```typescript
const response = await fetch(agentCoreEndpoint, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    prompt: userQuery,
    session_id: sessionId,
    context: {
      user_id: userId,
      user_role: userRole,
      active_member_id: activeMemberId
    }
  })
});

const result = await response.json();
console.log(result.result);
```

## Cleanup

### Destroy Agent

```powershell
# Dry run (see what would be destroyed)
agentcore destroy --agent healthlake-agent --dry-run

# Destroy agent
agentcore destroy --agent healthlake-agent

# Force destroy without confirmation
agentcore destroy --agent healthlake-agent --force

# Also delete ECR repository
agentcore destroy --agent healthlake-agent --delete-ecr-repo
```

## Troubleshooting

### Agent Configuration Issues

**Error**: `Could not find entrypoint module`

**Solution**: Ensure `agent_agentcore.py` exists and has the correct structure:

```python
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context):
    # Your logic
    return {"result": "..."}

if __name__ == "__main__":
    app.run()
```

### Deployment Failures

**Error**: `AWS authentication failed`

**Solution**: Ensure AWS profile is configured:

```powershell
aws configure --profile himssdemo
# Or set environment variable
$env:AWS_PROFILE = "himssdemo"
```

**Error**: `VPC configuration invalid`

**Solution**: Verify subnets and security groups exist and are in the same VPC.

### Runtime Errors

**Error**: `Module not found`

**Solution**: Ensure all dependencies are in `requirements.txt` including:
- `bedrock-agentcore`
- `strands-agents`
- All other dependencies

**Error**: `HealthLake access denied`

**Solution**: Verify IAM role has HealthLake permissions. AgentCore creates an execution role automatically, but you may need to add custom policies.

### Performance Issues

**Issue**: Slow cold starts

**Solution**: 
- Use provisioned concurrency (configure in AgentCore settings)
- Optimize imports in agent code
- Consider using Lambda SnapStart (if available)

## Cost Optimization

- **Idle Timeout**: Configure shorter idle timeout for dev environments
  ```powershell
  agentcore configure --idle-timeout 300 --name healthlake-agent
  ```

- **Max Lifetime**: Set appropriate max lifetime
  ```powershell
  agentcore configure --max-lifetime 3600 --name healthlake-agent
  ```

- **Right-size Memory**: Monitor CloudWatch metrics and adjust Lambda memory

## Comparison: AgentCore vs ECS Fargate

| Feature | AgentCore | ECS Fargate |
|---------|-----------|-------------|
| Deployment | Single CLI command | Multiple AWS services setup |
| Scaling | Automatic serverless | Manual configuration |
| Cold Start | ~2-5 seconds | Always warm |
| Cost | Pay per invocation | Pay for running time |
| Maintenance | Fully managed | Manual updates |
| VPC Support | Built-in | Manual configuration |
| Best For | Variable traffic | Consistent traffic |

## Resources

- **AgentCore Documentation**: Use `search_agentcore_docs` MCP tool
- **Configuration File**: `.bedrock_agentcore.yaml`
- **Agent Code**: `agent_agentcore.py`
- **Original Agent**: `agent.py`
- **CloudWatch Logs**: `/aws/lambda/healthlake-agent-*`

## Next Steps

1. Deploy the agent using the PowerShell script
2. Test with sample queries
3. Integrate with your frontend
4. Monitor performance in CloudWatch
5. Set up alarms for errors and latency
