# Claude Code Configuration

## Plugin Install (Recommended)

```bash
/plugin marketplace add aws-samples/amazon-bedrock-agents-healthcare-lifesciences
/plugin install hcls-agents
```

This loads all HCLS skills and MCP servers automatically.

## Manual Setup

Copy `.mcp.json` to your project root or `~/.claude/` for global config.

## What You Get

- HCLS domain skills loaded into context (genomics, drug discovery, clinical trials, etc.)
- MCP servers connected: AWS Knowledge, AgentCore docs, Strands docs, HealthOmics
- Additional MCP servers available in `mcp-servers/` (configure as needed)
