# OLS MCP Server Integration - Quick Reference

Complete toolkit for deploying and managing the OLS (Ontology Lookup Service) MCP Server for the Terminology Agent.

## 📁 Files Overview

### Core Deployment Scripts

| File | Purpose | Usage |
|------|---------|-------|
| `deploy_ols_mcp_server.py` | Deploy OLS MCP Server to AgentCore Runtime | `python deploy_ols_mcp_server.py` |
| `check_ols_mcp_deployment.py` | Check if OLS MCP Server is deployed | `python check_ols_mcp_deployment.py` |
| `test_ols_client.py` | Test deployed OLS MCP Server | `python test_ols_client.py` |
| `cleanup_ols_mcp.py` | Remove OLS MCP Server deployment | `python cleanup_ols_mcp.py` |
| `ols_utils.py` | Utility functions for Cognito auth & SSM | (Imported by other scripts) |

### Agent Code

| File | Purpose |
|------|---------|
| `patterns/strands-single-agent/terminology_agent_with_ols.py` | Agent code with OLS + Gateway tools |
| `patterns/strands-single-agent/basic_agent.py` | Default agent code (Gateway only) |

### Documentation

| File | Description |
|------|-------------|
| `ITERATIVE_DEPLOYMENT.md` | **Complete guide** for iterative deployment workflow |
| `OLS_MCP_DEPLOYMENT.md` | Detailed OLS MCP Server deployment documentation |
| `README_OLS_MCP.md` | This file - quick reference |

---

## 🚀 Quick Start (3 Commands)

```bash
# 1. Check if OLS MCP Server is deployed
python check_ols_mcp_deployment.py

# 2. Deploy OLS MCP Server (if not deployed)
python deploy_ols_mcp_server.py

# 3. Test the deployment
python test_ols_client.py
```

---

## 📋 Command Reference

### Check Deployment Status

```bash
# Check with formatted output
python check_ols_mcp_deployment.py

# Check with JSON output
python check_ols_mcp_deployment.py --json

# Check different stack
python check_ols_mcp_deployment.py --stack-name my-stack
```

**Exit codes:**
- `0` = Deployed
- `1` = Not deployed

### Deploy OLS MCP Server

```bash
# Deploy (will skip if already deployed)
python deploy_ols_mcp_server.py

# Force redeploy
python deploy_ols_mcp_server.py --force-redeploy

# Deploy to different stack
python deploy_ols_mcp_server.py --stack-name my-stack

# Custom tool name
python deploy_ols_mcp_server.py --tool-name my-ols-server
```

**Prerequisites:**
- CDK stack must be deployed first
- Docker must be running
- OLS source code must be available

**Time:** ~5-10 minutes

**Creates:**
- AgentCore Runtime with OLS MCP Server
- ECR repository with Docker image
- SSM parameters:
  - `/{stack}/ols-mcp-server/agent-arn`
  - `/{stack}/ols-mcp-server/agent-id`
  - `/{stack}/ols-mcp-server/mcp-url`

### Test OLS MCP Server

```bash
# Test deployment
python test_ols_client.py

# Test different stack
python test_ols_client.py --stack-name my-stack
```

**What it tests:**
- ✅ MCP server connectivity
- ✅ OAuth2 authentication
- ✅ 7 OLS tools availability
- ✅ Tool invocations with sample queries

### Cleanup Deployment

```bash
# Cleanup with confirmation
python cleanup_ols_mcp.py

# Force cleanup (no confirmation)
python cleanup_ols_mcp.py --force

# Cleanup different stack
python cleanup_ols_mcp.py --stack-name my-stack
```

**Removes:**
- AgentCore Runtime
- SSM parameters
- Does NOT remove ECR repository (delete manually if needed)

---

## 🔧 Integration with Agent

### Using OLS Tools in Agent Code

```python
from ols_utils import get_access_token, get_ssm_parameter
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

# Get MCP URL and token
mcp_url = get_ssm_parameter("/terminology-agent/ols-mcp-server/mcp-url")
access_token = get_access_token("terminology-agent")

# Create OLS MCP client
ols_client = MCPClient(
    lambda: streamablehttp_client(
        url=mcp_url,
        headers={"Authorization": f"Bearer {access_token}"}
    ),
    prefix="ols"
)

# Use with agent
agent = Agent(
    model=model,
    tools=[ols_client, other_tools],
    system_prompt="Your agent prompt..."
)
```

### Available OLS Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ols_search_terms` | Search across ontologies | query, ontology, rows |
| `ols_get_ontology_info` | Get ontology metadata | ontology_id |
| `ols_search_ontologies` | Find ontologies | search, size |
| `ols_get_term_info` | Get term details | id (IRI/short form) |
| `ols_get_term_children` | Get child terms | term_iri, ontology |
| `ols_get_term_ancestors` | Get parent terms | term_iri, ontology |
| `ols_find_similar_terms` | Find similar terms | term_iri, ontology |

---

## 🔑 Authentication Flow

The OLS MCP Server uses the **same Cognito authentication** as your CDK stack:

```
1. CDK Stack creates Cognito User Pool + Machine Client
   └─> Stores credentials in SSM/Secrets Manager

2. deploy_ols_mcp_server.py retrieves Cognito config
   └─> Configures OLS MCP Server with JWT auth

3. Agent/Client gets OAuth2 token
   └─> Uses token to call both Gateway AND OLS

4. OLS MCP Server validates JWT token
   └─> Provides access to 7 OLS tools
```

**Key points:**
- Same token works for Gateway and OLS
- Token uses M2M (client credentials) flow
- No user interaction required
- Tokens auto-refresh

---

## 📊 Monitoring & Debugging

### Check CloudWatch Logs

```bash
# Get Agent ID
python check_ols_mcp_deployment.py --json | jq -r '.agent_id'

# View logs
aws logs tail /aws/lambda/ols-mcp-server --follow
```

### Verify SSM Parameters

```bash
# List all OLS parameters
aws ssm describe-parameters \
  --filters "Key=Name,Values=/terminology-agent/ols-mcp-server" \
  | jq -r '.Parameters[].Name'

# Get specific parameter
aws ssm get-parameter \
  --name /terminology-agent/ols-mcp-server/mcp-url \
  | jq -r '.Parameter.Value'
```

### Test Authentication

```python
from ols_utils import get_access_token

# Get token
token = get_access_token("terminology-agent")
print(f"Token: {token[:50]}...")

# Decode token (optional)
import base64
import json

parts = token.split('.')
payload = json.loads(base64.b64decode(parts[1] + '=='))
print(f"Scopes: {payload.get('scope')}")
print(f"Client: {payload.get('client_id')}")
```

---

## 🔄 Common Workflows

### First Time Setup

```bash
cd agents_catalog/34-Terminology-agent

# 1. Deploy CDK stack (if not already)
cd infra-cdk && npx cdk deploy && cd ..

# 2. Deploy OLS MCP Server
python deploy_ols_mcp_server.py

# 3. Test
python test_ols_client.py
```

### Check Status

```bash
# Quick check
python check_ols_mcp_deployment.py

# Detailed check with logs
python check_ols_mcp_deployment.py && \
  python test_ols_client.py
```

### Update OLS MCP Server

```bash
# Option 1: Clean then redeploy
python cleanup_ols_mcp.py
python deploy_ols_mcp_server.py

# Option 2: Force redeploy
python deploy_ols_mcp_server.py --force-redeploy
```

### Troubleshoot Issues

```bash
# 1. Check deployment
python check_ols_mcp_deployment.py

# 2. Verify SSM parameters
aws ssm get-parameter --name /terminology-agent/ols-mcp-server/mcp-url

# 3. Test connectivity
python test_ols_client.py

# 4. Check logs
aws logs tail /aws/lambda/ols-mcp-server --follow
```

---

## 🐛 Troubleshooting

### "OLS MCP server not found"

**Cause:** Source code not available

**Solution:**
```bash
cd agents_catalog/28-Research-agent-biomni-gateway-tools/mcp-servers/ebi-ols-lookup
git clone https://github.com/seandavi/ols-mcp-server.git ols
```

### "403 Forbidden" when testing

**Causes:**
- AWS credentials issue
- Cognito configuration issue
- Token expired

**Solutions:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify Cognito config
aws ssm get-parameter --name /terminology-agent/machine_client_id

# Test token generation
python -c "from ols_utils import get_access_token; print(get_access_token()[:50])"
```

### "Runtime not found" but parameters exist

**Cause:** Stale SSM parameters

**Solution:**
```bash
# Cleanup stale parameters
python cleanup_ols_mcp.py --force

# Redeploy
python deploy_ols_mcp_server.py
```

### Agent doesn't use OLS tools

**Check agent logs:**
```bash
# Look for "Creating OLS MCP client" message
aws logs filter-pattern "OLS MCP client" \
  --log-group-name /aws/lambda/terminology-agent-runtime
```

**Common causes:**
1. MCP URL not in SSM → Run `python check_ols_mcp_deployment.py`
2. Token doesn't have correct scopes → Check Cognito resource server
3. Network connectivity → Test with `python test_ols_client.py`

---

## 📚 Additional Resources

### Documentation
- **Iterative Deployment Guide**: `ITERATIVE_DEPLOYMENT.md` - Complete workflow
- **OLS Deployment Guide**: `OLS_MCP_DEPLOYMENT.md` - Detailed technical docs
- **Agent Integration**: `patterns/strands-single-agent/terminology_agent_with_ols.py`

### External Links
- [EBI OLS API](https://www.ebi.ac.uk/ols4/) - Ontology Lookup Service
- [MCP Protocol](https://modelcontextprotocol.io/) - Model Context Protocol
- [Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/) - AWS Documentation

---

## 🎯 Next Steps

1. ✅ Deploy OLS MCP Server: `python deploy_ols_mcp_server.py`
2. ✅ Test deployment: `python test_ols_client.py`
3. ✅ Update agent code: Copy `terminology_agent_with_ols.py`
4. ✅ Redeploy backend: `cd infra-cdk && npx cdk deploy`
5. 🎯 Customize for your use case
6. 🎯 Add monitoring & alerts
7. 🎯 Build frontend integration

---

## 💡 Tips

- Use `--json` flag for scripting/automation
- Check status before deploying to avoid duplicates
- Test after every deployment
- Keep Cognito credentials secure
- Monitor CloudWatch logs for issues
- Use `--force-redeploy` sparingly

---

## 🆘 Getting Help

If you encounter issues:

1. Check this README first
2. Read `ITERATIVE_DEPLOYMENT.md` for detailed guidance
3. Review `OLS_MCP_DEPLOYMENT.md` for technical details
4. Check CloudWatch Logs
5. Verify SSM parameters exist and are correct
6. Test with `test_ols_client.py`

For bugs or feature requests, check the repository issues.
