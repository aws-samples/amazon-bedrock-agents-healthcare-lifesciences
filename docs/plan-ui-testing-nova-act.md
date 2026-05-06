# Plan: Secure UI Testing with Nova Act + FAST

## Current State (as of May 6, 2026)

✅ **FAST deployed** to sandbox account:
- Frontend: `https://main.d3tz1o16gqjqs7.amplifyapp.com`
- Cognito User Pool: `us-east-1_zvMTmQzIM`
- Backend Runtime: `hcls_agents_ui_FASTAgent-Wy4Z8hHmYn`
- Amplify App ID: `d3tz1o16gqjqs7`

✅ **4 Phase 1 agents deployed** on AgentCore (same account)

❌ **FAST frontend needs agent selector** — currently only shows its own default agent

## Architecture (Target)

```
┌─────────────────────────────────────────────────────────────┐
│  Nova Act (headless browser in AWS)                          │
│  → Navigates to Amplify HTTPS URL                           │
│  → Logs in via Cognito                                      │
│  → Selects agent from dropdown                              │
│  → Sends test queries, verifies responses                   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS Amplify (FAST Frontend)                                 │
│  • React + TypeScript                                        │
│  • Cognito authentication (secure, no 0.0.0.0/0)           │
│  • Agent selector dropdown (discovers all runtimes)         │
│  • Chat interface                                            │
│  URL: https://main.d3tz1o16gqjqs7.amplifyapp.com           │
└─────────────────────────────────────────────────────────────┘
         │ (AgentCore invoke API)
         ▼
┌─────────────────────────────────────────────────────────────┐
│  AgentCore Runtimes                                          │
│  • enrollment_pulse                                          │
│  • clinical_prior_auth                                       │
│  • clinical_pvq                                              │
│  • medical_device_agent                                      │
│  • hcls_agents_ui_FASTAgent (default)                       │
└─────────────────────────────────────────────────────────────┘
```

## Next Steps

### 1. Add agent selector to FAST frontend (~1-2 hours)

Modify `frontend/src/` to:
- Call `bedrock-agentcore-control` `listAgentRuntimes` API
- Show dropdown in sidebar to select which agent to chat with
- Pass selected agent ARN when invoking

Reference: `agentcore_template/app.py` lines 43+ (`fetch_agent_runtimes`)

### 2. Redeploy frontend

```bash
cd fast-agentcore
python scripts/deploy-frontend.py
```

### 3. Update Nova Act tests

Point tests at the Amplify URL with Cognito login flow:
```python
with NovaAct(starting_page="https://main.d3tz1o16gqjqs7.amplifyapp.com", headless=True) as nova:
    # Login
    nova.act("Enter 'admin' in username field")
    nova.act("Enter password and click sign in")
    # Select agent
    nova.act("Select 'enrollment_pulse' from the agent dropdown")
    # Test
    nova.act("Type 'What is enrollment status?' and send")
    nova.act("Verify response contains site names")
```

### 4. Run tests in CI/CD

- Store `NOVA_ACT_API_KEY` in Secrets Manager
- GitHub Actions or CodeBuild triggers on PR merge
- Tests run headless against the deployed Amplify URL

## Security

- ✅ HTTPS only (Amplify)
- ✅ Cognito authentication required
- ✅ No public ALB or 0.0.0.0/0
- ✅ Nova Act API key in env var / Secrets Manager
- ✅ IAM roles for AgentCore access
