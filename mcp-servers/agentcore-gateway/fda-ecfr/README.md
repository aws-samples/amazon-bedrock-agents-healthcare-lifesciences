# FDA eCFR MCP Server — AgentCore Gateway

3 tools for retrieving FDA regulations (Title 21 CFR) from the public eCFR API, deployed as Lambda targets behind AgentCore Gateway.

## Tools Available

| Tool | What it does |
|------|-------------|
| `get_cfr_section` | Retrieve full text of a specific CFR section (e.g., 21 CFR 312.23) |
| `search_cfr` | Search FDA regulations for terms or concepts |
| `get_cfr_part_structure` | Get table of contents for a CFR part |

### Example Queries

- "Get 21 CFR 312.23 for IND content requirements"
- "Search for informed consent requirements in Part 50"
- "What sections exist in 21 CFR Part 312?"

## Architecture

```
Client (Claude Code / Kiro / Amazon Quick)
    |
    | HTTPS + JWT token
    v
AgentCore Gateway (MCP protocol)
    |
    | Lambda invocation
    v
fda-ecfr Lambda (Python)
    |
    | HTTPS (no auth required)
    v
eCFR Public API (https://www.ecfr.gov/api/versioner/v1/)
```

## Prerequisites

| Requirement | Details |
|-------------|---------|
| AWS CLI | Configured with appropriate credentials |
| @aws/agentcore CLI | `npm install -g @aws/agentcore` |
| Python 3.12+ | For Lambda runtime |
| AWS Account | Permissions: CloudFormation, Lambda, IAM, Bedrock AgentCore |
| Region | `us-east-1` or `us-west-2` (AgentCore availability) |

## Deployment

### Quick Start

```bash
cd mcp-servers/agentcore-gateway/fda-ecfr
./deploy.sh
```

### What the Deploy Script Does

1. Deploys Lambda function stack (`cfn/lambda.yaml`)
2. Deploys Cognito authentication stack (`cfn/cognito.yaml`)
3. Registers Lambda as AgentCore Gateway target with tool schemas
4. Stores endpoint URL in SSM Parameter Store

### SSM Parameters Created

| Parameter | Description |
|-----------|-------------|
| `/app/fda-ecfr/agentcore/mcp_url` | MCP endpoint URL |
| `/app/fda-ecfr/agentcore/machine_client_id` | Cognito client ID |
| `/app/fda-ecfr/agentcore/cognito_secret` | Cognito client secret |
| `/app/fda-ecfr/agentcore/cognito_domain` | Cognito domain |

## Connecting to Your AI Assistant

### Step 1: Get an access token

```bash
source get-token.sh
# Sets: FDA_ECFR_TOKEN, FDA_ECFR_URL
```

### Step 2: Connect

#### Claude Code

```bash
claude mcp add --transport http \
  --header "Authorization: Bearer $FDA_ECFR_TOKEN" \
  fda-ecfr "$FDA_ECFR_URL"
```

#### Kiro

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "fda-ecfr": {
      "transportType": "http",
      "url": "<FDA_ECFR_URL>",
      "headers": {
        "Authorization": "Bearer ${FDA_ECFR_TOKEN}"
      }
    }
  }
}
```

## Data Source

- [eCFR API Documentation](https://www.ecfr.gov/developers)
- All CFR data is U.S. Government public domain
- No API key or rate limiting (reasonable use expected)

## Cleanup

```bash
aws cloudformation delete-stack --stack-name fda-ecfr-lambda
aws cloudformation delete-stack --stack-name fda-ecfr-cognito
aws ssm delete-parameters --names \
  "/app/fda-ecfr/agentcore/mcp_url" \
  "/app/fda-ecfr/agentcore/machine_client_id" \
  "/app/fda-ecfr/agentcore/cognito_secret" \
  "/app/fda-ecfr/agentcore/cognito_domain"
```
