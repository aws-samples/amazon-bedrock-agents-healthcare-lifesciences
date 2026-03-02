# OLS MCP Server Deployment Guide

This guide explains how to deploy the OLS (Ontology Lookup Service) MCP Server to Amazon Bedrock AgentCore Runtime for use with the Terminology Agent.

## Overview

The OLS MCP Server provides access to the EBI Ontology Lookup Service, offering tools for:
- Searching medical/biological terms across 200+ ontologies
- Getting detailed ontology information
- Retrieving term hierarchies and relationships
- Finding similar terms using LLM embeddings

## Prerequisites

1. **CDK Stack Deployed**: The Terminology Agent CDK stack must be deployed first
   ```bash
   cd infra-cdk
   cdk deploy
   ```

2. **Python Packages**: Install required Python packages
   ```bash
   pip install boto3 requests mcp bedrock-agentcore-starter-toolkit
   ```

3. **AWS Credentials**: Ensure you have AWS credentials configured
   ```bash
   aws sts get-caller-identity
   ```

4. **Docker Running**: Docker must be running for building container images
   ```bash
   docker ps
   ```

## Cognito Integration

The deployment automatically uses the existing Cognito User Pool from the Terminology Agent stack:

### SSM Parameters Used

The deployment retrieves these parameters from `/terminology-agent/` prefix:
- `cognito-user-pool-id` - User Pool ID
- `machine_client_id` - Machine-to-Machine client ID
- `machine_client_secret` - M2M client secret (from Secrets Manager)
- `cognito_provider` - Cognito domain

### Authentication Flow

The OLS MCP Server uses **Cognito OAuth2 Client Credentials flow** for authentication:

1. **Token Acquisition**: The deployment script retrieves M2M credentials from SSM/Secrets Manager
2. **JWT Authorization**: AgentCore Runtime validates JWTs from the machine client
3. **Authorized Access**: Only requests with valid tokens from the allowed client can access the MCP server

This ensures secure access while reusing the existing authentication infrastructure.

## Deployment Steps

### Step 1: Deploy OLS MCP Server

Run the deployment script:

```bash
cd agents_catalog/34-Terminology-agent
python deploy_ols_mcp_server.py
```

**What happens during deployment:**
1. ✅ Copies OLS MCP server source code
2. ✅ Generates requirements.txt from pyproject.toml
3. ✅ Configures Cognito authentication (reuses existing setup)
4. ✅ Builds Docker image with dependencies
5. ✅ Pushes image to Amazon ECR
6. ✅ Deploys to AgentCore Runtime
7. ✅ Stores configuration in SSM Parameter Store

**Expected output:**
```
================================================================================
🚀 Deploying OLS MCP Server to AgentCore Runtime
================================================================================

📍 AWS Region: us-east-1
✓ OLS MCP server found at .../ols
📁 Copying OLS MCP server...
✓ Source code copied
📝 Generating requirements.txt...
✓ Requirements file generated
🔍 Verifying required files...
✓ server.py
✓ models.py
✓ __init__.py
✓ requirements.txt
🔐 Configuring Cognito authentication...
✓ User Pool ID: us-east-1_xxxxx
✓ Client ID: xxxxx
✓ Discovery URL: https://cognito-idp.us-east-1.amazonaws.com/...
⚙️  Configuring AgentCore Runtime...
✓ Configuration completed
🚀 Launching MCP server to AgentCore Runtime...
   This may take several minutes...
✓ Launch completed

📋 Agent ARN: arn:aws:bedrock-agentcore:us-east-1:xxxx:runtime/xxxxx
📋 Agent ID: xxxxx
💾 Storing configuration in Parameter Store...
✓ Configuration stored

================================================================================
✅ OLS MCP Server Deployment Complete!
================================================================================

📍 Agent ARN: arn:aws:bedrock-agentcore:us-east-1:xxxx:runtime/xxxxx
📍 Agent ID: xxxxx
📍 MCP URL: https://bedrock-agentcore.us-east-1.amazonaws.com/...

💡 Test the deployment with: python test_ols_client.py
```

### Step 2: Test the Deployment

Run the test client to verify the deployment:

```bash
python test_ols_client.py
```

**What the test does:**
1. ✅ Retrieves MCP server configuration from SSM
2. ✅ Gets access token using Cognito M2M flow
3. ✅ Connects to the deployed MCP server
4. ✅ Lists available tools
5. ✅ Tests tool invocations with sample queries

**Expected output:**
```
================================================================================
🧪 Testing OLS MCP Server
================================================================================

📍 AWS Region: us-east-1
🔍 Retrieving MCP server configuration...
✓ Agent ARN: arn:aws:bedrock-agentcore:us-east-1:xxxx:runtime/xxxxx
✓ MCP URL: https://bedrock-agentcore.us-east-1.amazonaws.com/...
🔐 Getting access token...
✓ Access token retrieved
🔌 Connecting to MCP server...
🔄 Initializing MCP session...
✓ MCP session initialized
📋 Listing available tools...

================================================================================
🔧 Available MCP Tools:
================================================================================

• search_terms
  Description: Search for terms across ontologies using the OLS search API
  Parameters: query, ontology, exact_match, include_obsolete, rows

• get_ontology_info
  Description: Get detailed information about a specific ontology
  Parameters: ontology_id

• search_ontologies
  Description: Search for available ontologies
  Parameters: search, page, size

• get_term_info
  Description: Get detailed information about a specific term
  Parameters: id

• get_term_children
  Description: Get direct children of a specific term
  Parameters: term_iri, ontology, include_obsolete, size

• get_term_ancestors
  Description: Get ancestor terms (parents) of a specific term
  Parameters: term_iri, ontology, include_obsolete, size

• find_similar_terms
  Description: Find terms similar to the given term using LLM embeddings
  Parameters: term_iri, ontology, size

✅ Found 7 tools available

================================================================================
🧪 Testing MCP Tools:
================================================================================

1️⃣ Testing search_terms('myocardial infarction')...
   ✓ Result: {...}

2️⃣ Testing get_ontology_info('mondo')...
   ✓ Result: {...}

3️⃣ Testing search_ontologies('disease')...
   ✓ Result: {...}

4️⃣ Testing search_terms('diabetes')...
   ✓ Result: {...}

================================================================================
✅ MCP Server Testing Complete!
================================================================================
```

## Using with Terminology Agent

### Step 3: Integrate with Agent Code

Now you can use the OLS MCP server in your agent code. Here's an example:

```python
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

from ols_utils import get_access_token, get_ssm_parameter

# Get MCP server URL and token
mcp_url = get_ssm_parameter("/terminology-agent/ols-mcp-server/mcp-url")
bearer_token = get_access_token("terminology-agent")

headers = {
    "authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json"
}

# Create MCP client
client = MCPClient(
    lambda: streamablehttp_client(mcp_url, headers)
)

# Create agent with OLS tools
with client:
    tools = client.list_tools_sync()

    model = BedrockModel(
        model_id="global.anthropic.claude-sonnet-4-20250514-v1:0",
        temperature=0.7
    )

    agent = Agent(
        model=model,
        tools=tools,
        system_prompt="""You are a medical terminology expert with access to
        the EBI Ontology Lookup Service. Help standardize and disambiguate
        medical terms."""
    )

    # Use the agent
    result = agent("What is the MONDO ID for myocardial infarction?")
    print(result.message['content'][0]['text'])
```

## Configuration Reference

### SSM Parameters Created

After deployment, these parameters are available:

| Parameter | Description |
|-----------|-------------|
| `/terminology-agent/ols-mcp-server/agent-arn` | Agent ARN for the MCP server |
| `/terminology-agent/ols-mcp-server/agent-id` | Agent ID |
| `/terminology-agent/ols-mcp-server/mcp-url` | Full MCP invocation URL |

### Available OLS Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `search_terms` | Search across 200+ ontologies | query, ontology, rows |
| `get_ontology_info` | Get ontology metadata | ontology_id |
| `search_ontologies` | Find available ontologies | search, size |
| `get_term_info` | Get detailed term information | id (IRI/short form/OBO ID) |
| `get_term_children` | Get child terms in hierarchy | term_iri, ontology |
| `get_term_ancestors` | Get parent/ancestor terms | term_iri, ontology |
| `find_similar_terms` | Find semantically similar terms | term_iri, ontology |

### Priority Ontologies for Medical Use

| Ontology | ID | Description |
|----------|-----|-------------|
| MONDO | `mondo` | Disease classification |
| HPO | `hp` | Human phenotypes |
| GO | `go` | Gene Ontology |
| ChEBI | `chebi` | Chemical entities |
| EFO | `efo` | Experimental factors |

## Troubleshooting

### Issue: "OLS MCP server not found"

**Solution:** Ensure the OLS server is cloned:
```bash
cd agents_catalog/28-Research-agent-biomni-gateway-tools/mcp-servers/ebi-ols-lookup
git clone https://github.com/seandavi/ols-mcp-server.git ols
```

### Issue: "bedrock_agentcore_starter_toolkit not found"

**Solution:** Install the toolkit:
```bash
pip install bedrock-agentcore-starter-toolkit
```

### Issue: "403 Forbidden" when testing

**Solution:** Check that your AWS credentials have permissions for:
- Bedrock AgentCore
- SSM Parameter Store
- Secrets Manager
- Cognito

### Issue: "Access token expired"

**Solution:** The script automatically refreshes tokens. If issues persist:
1. Verify Cognito machine client has correct scopes
2. Check resource server configuration in Cognito

## Cleanup

To remove the deployed MCP server:

```bash
# Delete AgentCore Runtime
aws bedrock-agentcore-control delete-runtime --agent-id <agent-id>

# Delete SSM parameters
aws ssm delete-parameter --name /terminology-agent/ols-mcp-server/agent-arn
aws ssm delete-parameter --name /terminology-agent/ols-mcp-server/agent-id
aws ssm delete-parameter --name /terminology-agent/ols-mcp-server/mcp-url

# Delete ECR repository (if needed)
aws ecr delete-repository --repository-name ols-mcp-server --force
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Terminology Agent                         │
│  ┌────────────────────┐         ┌─────────────────────┐     │
│  │   Frontend (CDK)   │         │   Backend (CDK)     │     │
│  │                    │         │                     │     │
│  │  • CloudFront      │         │  • AgentCore        │     │
│  │  • S3              │         │    Runtime          │     │
│  │  • Cognito Auth    │         │  • DynamoDB         │     │
│  └────────────────────┘         │  • API Gateway      │     │
│                                  │  • Lambda           │     │
│                                  └─────────────────────┘     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Uses existing Cognito
                           │
                  ┌────────▼─────────┐
                  │  OLS MCP Server  │
                  │  (AgentCore RT)  │
                  │                  │
                  │  • Hosted on     │
                  │    AgentCore     │
                  │  • JWT Auth      │
                  │  • 7 OLS Tools   │
                  └──────────────────┘
                           │
                           │ Accesses
                           │
                  ┌────────▼─────────┐
                  │  EBI OLS API     │
                  │  (External)      │
                  │                  │
                  │  • 200+ ontologies│
                  │  • Public access │
                  └──────────────────┘
```

## Next Steps

1. ✅ Deploy CDK stack: `cd infra-cdk && cdk deploy`
2. ✅ Deploy OLS MCP server: `python deploy_ols_mcp_server.py`
3. ✅ Test deployment: `python test_ols_client.py`
4. ✅ Integrate with agent: Use code example above
5. ✅ Customize system prompt for your use case

## Support

For issues or questions:
- Check CloudWatch Logs for AgentCore Runtime
- Review CDK deployment outputs
- Verify Cognito configuration
- Test with `test_ols_client.py`
