# Kiro Configuration

## Setup

Copy this folder's contents to your project's `.kiro/` directory, or reference via local path in your Kiro settings.

```bash
cp -r platforms/kiro/ .kiro/
```

## What You Get

- `POWER.md` — Power definition for the HCLS toolkit
- `mcp.json` — MCP server connections
- `steering/` — Domain-specific steering documents (adapted from skills/)

## Existing Kiro Power

This repo also maintains a Kiro Power at `powers/hcls-agentcore-builder/` which provides agent development guidance. The two are complementary:
- `powers/hcls-agentcore-builder/` — focused on building agents with AgentCore
- `platforms/kiro/` — broader HCLS domain skills and MCP tools
