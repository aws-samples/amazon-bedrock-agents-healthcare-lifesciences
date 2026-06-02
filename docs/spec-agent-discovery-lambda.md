# Agent Discovery Lambda — Spec

## Purpose

Returns a list of all AgentCore runtimes deployed in the account so the FAST React frontend can render an agent selector dropdown.

## Lambda Function

**Runtime**: Python 3.12  
**Handler**: `index.handler`  
**Timeout**: 10 seconds  
**Memory**: 128 MB

```python
import json
import boto3

def handler(event, context):
    """List all AgentCore runtimes in the account."""
    client = boto3.client("bedrock-agentcore-control")
    
    agents = []
    next_token = None
    
    while True:
        params = {"maxResults": 100}
        if next_token:
            params["nextToken"] = next_token
            
        response = client.list_agent_runtimes(**params)
        
        for runtime in response.get("agentRuntimes", []):
            agents.append({
                "name": runtime["agentRuntimeName"],
                "arn": runtime["agentRuntimeArn"],
                "status": runtime.get("status", "UNKNOWN"),
            })
        
        next_token = response.get("nextToken")
        if not next_token:
            break
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"agents": agents}),
    }
```

## IAM Role Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:ListAgentRuntimes"
      ],
      "Resource": "*"
    }
  ]
}
```

Trust policy: `lambda.amazonaws.com`

## API Gateway

**Method**: `GET /agents`  
**Auth**: Cognito User Pool Authorizer (same as existing feedback API)  
**Integration**: Lambda proxy  

Attach to the existing FAST API Gateway (`feedbackApiUrl`):
```
https://hwvpfvcmic.execute-api.us-east-1.amazonaws.com/prod/agents
```

## Response Format

```json
{
  "agents": [
    {
      "name": "enrollment_pulse",
      "arn": "arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT>:runtime/enrollment_pulse-6YHCrd3h6H",
      "status": "ACTIVE"
    },
    {
      "name": "clinical_prior_auth",
      "arn": "arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT>:runtime/clinical_prior_auth-0I0JTA3PT0",
      "status": "ACTIVE"
    },
    {
      "name": "clinical_pvq",
      "arn": "arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT>:runtime/clinical_pvq-F5sm875N80",
      "status": "ACTIVE"
    },
    {
      "name": "medical_device_agent",
      "arn": "arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT>:runtime/medical_device_agent-YiCRKk2g4F",
      "status": "ACTIVE"
    }
  ]
}
```

## Frontend Integration

```typescript
// In ChatInterface.tsx or a new hook
const [agents, setAgents] = useState<{name: string, arn: string}[]>([])
const [selectedArn, setSelectedArn] = useState<string>("")

useEffect(() => {
  async function fetchAgents() {
    const token = auth.user?.access_token
    const res = await fetch(`${config.feedbackApiUrl}agents`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    const data = await res.json()
    setAgents(data.agents.filter(a => a.status === "ACTIVE"))
    if (data.agents.length > 0) setSelectedArn(data.agents[0].arn)
  }
  fetchAgents()
}, [auth])

// Dropdown in JSX
<select value={selectedArn} onChange={e => {
  setSelectedArn(e.target.value)
  // Recreate client with new ARN
  setClient(new AgentCoreClient({ runtimeArn: e.target.value, region, pattern }))
  setMessages([]) // Clear chat on agent switch
}}>
  {agents.map(a => <option key={a.arn} value={a.arn}>{a.name}</option>)}
</select>
```

## CDK Addition (in backend-stack.ts)

```typescript
// Add to existing API Gateway
const listAgentsLambda = new PythonFunction(this, "ListAgentsLambda", {
  runtime: Runtime.PYTHON_3_12,
  entry: path.join(__dirname, "../lambdas/list-agents"),
  handler: "handler",
  timeout: Duration.seconds(10),
  memorySize: 128,
});

listAgentsLambda.addToRolePolicy(new PolicyStatement({
  actions: ["bedrock-agentcore:ListAgentRuntimes"],
  resources: ["*"],
}));

// Add GET /agents route
api.root.addResource("agents").addMethod("GET", 
  new LambdaIntegration(listAgentsLambda),
  { authorizer: cognitoAuthorizer }
);
```

## Files to Create/Modify

1. `infra-cdk/lambdas/list-agents/index.py` — Lambda code (above)
2. `infra-cdk/lib/backend-stack.ts` — Add Lambda + API route
3. `frontend/src/components/chat/ChatInterface.tsx` — Add dropdown + fetch
4. Redeploy: `cdk deploy --all` then `python scripts/deploy-frontend.py`
