# Biomni Research Tools — AgentCore Gateway

30+ biomedical database query tools deployed as an MCP endpoint via AgentCore Gateway.

## Tools Available

Queries across databases including: UniProt, Reactome, STRING, DrugBank, ChEMBL, KEGG, Ensembl, GWAS Catalog, Human Protein Atlas, GTEx, PDB, AlphaFold, ClinVar, gnomAD, and more.

## Deployment

This server reuses the deployment pattern from [Agent 28 (Research/Biomni Gateway)](../../../agents_catalog/28-Research-agent-biomni-gateway-tools/).

**Follow steps 1-2 from the Agent 28 README:**

1. **Setup Agent Tools** — Clone Biomni schemas, prepare Lambda code
2. **Create Infrastructure** — Run `prereq.sh` to deploy CloudFormation stacks

```bash
cd agents_catalog/28-Research-agent-biomni-gateway-tools
uv sync
./scripts/prereq.sh
```

This creates:
- Lambda functions for database queries
- Cognito user pool for authentication
- AgentCore Gateway with MCP endpoint

## Connecting Your AI Assistant

After deployment, retrieve the Gateway URL from SSM:

```bash
aws ssm get-parameter --name /app/researchapp/agentcore/gateway_url --query Parameter.Value --output text
```

Add to your assistant's MCP config:

```json
{
  "mcpServers": {
    "biomni-research": {
      "type": "http",
      "url": "<GATEWAY_URL>"
    }
  }
}
```

Authentication requires a Cognito JWT token. See the Agent 28 README for OAuth2 configuration details.

## Source

Full implementation: [agents_catalog/28-Research-agent-biomni-gateway-tools/](../../../agents_catalog/28-Research-agent-biomni-gateway-tools/)
