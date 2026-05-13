---
name: hcls-get-started
description: Use when a developer asks how to get started building healthcare or life sciences agents, wants to understand the HCLS Agents Toolkit, or asks what's available in this repository. Also use when someone asks about genomics, drug discovery, clinical trials, or biomarker agents on AWS.
---

# Getting Started with the HCLS Agents Toolkit

## When to use this skill

- Developer asks "how do I build an HCLS agent?"
- Developer asks "what agents are available for healthcare/life sciences?"
- Developer wants to understand the toolkit's architecture and offerings

## Overview

The HCLS Agents Toolkit provides three types of resources:

1. **Skills** — Domain workflow knowledge (this directory: `skills/`)
2. **MCP Servers** — Domain tools accessible from any MCP client (`mcp-servers/`)
3. **Agent Catalog** — 36+ production-ready deployed agents (`agents_catalog/`)

## Choosing Your Path

| Goal | Start here |
|------|-----------|
| Build a new HCLS agent from scratch | Use `hcls-build-agent` skill + `agentcore_template/` |
| Deploy an existing catalog agent | Pick from `agents_catalog/`, follow its README |
| Connect domain tools to your IDE | Configure MCP servers from `mcp-servers/` |
| Run HCLS workflows without deploying | Use skills + MCP servers directly in your assistant |

## Architecture

Agents are composed from:
- **Skills** (knowledge) — SKILL.md files that teach workflows
- **MCP tools** (actions) — deployed via AgentCore Gateway/Runtime or configured from public servers
- **Agent reasoning** (orchestration) — system prompts + Strands framework + guardrails

## Key References

- Agent catalog: `agents_catalog/` (36+ agents across genomics, drug discovery, clinical trials, etc.)
- Deployment templates: `agentcore_template/` (backend) or [FAST](https://github.com/awslabs/fullstack-solution-template-for-agentcore) (full-stack)
- Framework: [Strands Agents](https://github.com/strands-agents/sdk-python)
- Infrastructure: [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/)

## Next Steps

1. Browse skills by domain: genomics, drug discovery, clinical trials, biomarker, terminology
2. Configure MCP servers for immediate tool access (see `mcp-servers/aws-public/` and `mcp-servers/third-party/`)
3. Use `hcls-build-agent` skill when ready to build a custom agent
4. Use `hcls-deploy-agent` skill when ready to deploy to production
