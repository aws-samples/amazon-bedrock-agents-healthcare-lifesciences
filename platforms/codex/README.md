# Codex Configuration

## Plugin Install

```bash
codex plugin marketplace add aws-samples/amazon-bedrock-agents-healthcare-lifesciences
codex plugin install hcls-agents
```

## Manual Setup

- Copy `AGENTS.md` to your project root
- Copy `config.toml` to your project's `.codex/` directory
- Copy `skill/` to `.agents/skills/`

## What You Get

- `AGENTS.md` — Agent instructions for HCLS domain workflows
- `config.toml` — MCP server configuration (TOML format)
- `skill/SKILL.md` — Master skill with domain references
