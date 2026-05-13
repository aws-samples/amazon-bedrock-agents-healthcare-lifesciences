# Amazon Q Desktop Configuration

## Skills Setup

Copy HCLS skills to the Q Desktop skills directory:

```bash
cp -r platforms/q-desktop/skills/* ~/.quickwork/skills/
```

## MCP Server Setup

1. Open Amazon Q Desktop
2. Go to **Settings → Capabilities**
3. Add MCP servers:

| Server | Type | URL/Command |
|--------|------|-------------|
| AWS Knowledge | HTTP | `https://knowledge-mcp.global.api.aws` |
| PubMed | HTTP | `https://pubmed.mcp.claude.com/mcp` |
| Open Targets | HTTP | `https://mcp.platform.opentargets.org/mcp` |
| AWS HealthOmics | stdio | `uvx awslabs.aws-healthomics-mcp-server@latest` |

For deployed HCLS MCP servers (Biomni Gateway, OLS), add the Gateway URL after deployment.

## What You Get

- HCLS domain skills accessible via natural language workflows
- MCP tools for biomedical research, literature search, and ontology lookup
- No agent deployment needed — skills + MCP servers work directly in Q Desktop
