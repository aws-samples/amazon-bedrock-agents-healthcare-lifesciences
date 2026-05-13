# Platform Configuration Adapters

Per-platform configuration files for AI coding assistants and end-user platforms. Each folder contains ready-to-use configs that connect the platform to HCLS skills and MCP servers.

## Supported Platforms

| Platform | Folder | Skills format | MCP config |
|----------|--------|---------------|------------|
| [Claude Code](claude-code/) | claude-code/ | SKILL.md via plugin install | `.mcp.json` |
| [Kiro](kiro/) | kiro/ | POWER.md + steering/ | `mcp.json` |
| [Codex](codex/) | codex/ | SKILL.md via .codex-plugin | `config.toml` |
| [Amazon Q Desktop](q-desktop/) | q-desktop/ | SKILL.md in ~/.quickwork/skills/ | Settings → Capabilities |

## Quick Setup

Run the interactive installer:

```bash
./setup.sh
```

This will:
1. Ask which platform you're using
2. Ask for global vs. project-level install
3. Copy the appropriate configuration files
4. Validate the setup

## Manual Setup

Each platform folder contains a README with manual setup instructions and the config files needed.

## What Gets Configured

Regardless of platform, you get:
- **Skills** — HCLS domain workflow guidance loaded into your assistant's context
- **MCP servers** — Connections to biomedical databases, ontology services, AWS documentation, and genomics tools
- **Rules** — Global HCLS agent behavior guidance (data handling, compliance awareness)
