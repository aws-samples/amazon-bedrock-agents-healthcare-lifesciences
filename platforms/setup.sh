#!/bin/bash
# Interactive setup script for HCLS Agents Toolkit
# Configures skills and MCP servers for your AI coding assistant

set -e

echo "============================================"
echo "  HCLS Agents Toolkit - Platform Setup"
echo "============================================"
echo ""
echo "This script configures HCLS domain skills and MCP servers"
echo "for your AI coding assistant."
echo ""

# Platform selection
echo "Which platform are you using?"
echo ""
echo "  1) Claude Code"
echo "  2) Kiro"
echo "  3) Codex"
echo "  4) Amazon Q Desktop"
echo "  5) Cursor"
echo ""
read -p "Select (1-5): " PLATFORM

# Scope selection
echo ""
echo "Install scope:"
echo ""
echo "  1) Project-level (current directory only)"
echo "  2) Global (all projects)"
echo ""
read -p "Select (1-2): " SCOPE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

case $PLATFORM in
  1) # Claude Code
    echo ""
    echo "For Claude Code, use the plugin install mechanism:"
    echo ""
    echo "  /plugin marketplace add aws-samples/amazon-bedrock-agents-healthcare-lifesciences"
    echo "  /plugin install hcls-agents"
    echo ""
    echo "This automatically loads skills and MCP servers."
    echo ""
    echo "For manual MCP config, copy .mcp.json to your project:"
    if [ "$SCOPE" = "1" ]; then
      cp "$SCRIPT_DIR/claude-code/.mcp.json" ./.mcp.json
      echo "  Copied .mcp.json to current directory."
    else
      mkdir -p ~/.claude
      cp "$SCRIPT_DIR/claude-code/.mcp.json" ~/.claude/.mcp.json
      echo "  Copied .mcp.json to ~/.claude/"
    fi
    ;;
  2) # Kiro
    if [ "$SCOPE" = "1" ]; then
      mkdir -p .kiro/steering
      cp "$SCRIPT_DIR/kiro/POWER.md" .kiro/
      cp "$SCRIPT_DIR/kiro/mcp.json" .kiro/settings/mcp.json 2>/dev/null || cp "$SCRIPT_DIR/kiro/mcp.json" .kiro/
      cp "$SCRIPT_DIR/kiro/steering/"* .kiro/steering/ 2>/dev/null || true
      echo "  Copied Kiro config to .kiro/"
    else
      mkdir -p ~/.kiro/steering
      cp "$SCRIPT_DIR/kiro/POWER.md" ~/.kiro/
      cp "$SCRIPT_DIR/kiro/mcp.json" ~/.kiro/
      cp "$SCRIPT_DIR/kiro/steering/"* ~/.kiro/steering/ 2>/dev/null || true
      echo "  Copied Kiro config to ~/.kiro/"
    fi
    ;;
  3) # Codex
    if [ "$SCOPE" = "1" ]; then
      cp "$SCRIPT_DIR/codex/AGENTS.md" ./AGENTS.md
      mkdir -p .agents/skills
      cp -r "$SCRIPT_DIR/codex/skill/"* .agents/skills/ 2>/dev/null || true
      echo "  Copied Codex config to current directory."
    else
      mkdir -p ~/.codex/skills
      cp -r "$SCRIPT_DIR/codex/skill/"* ~/.codex/skills/ 2>/dev/null || true
      echo "  Copied Codex config to ~/.codex/"
    fi
    ;;
  4) # Q Desktop
    mkdir -p ~/.quickwork/skills
    cp -r "$SCRIPT_DIR/q-desktop/skills/"* ~/.quickwork/skills/ 2>/dev/null || true
    echo "  Copied skills to ~/.quickwork/skills/"
    echo ""
    echo "  MCP servers must be added manually:"
    echo "  Open Q Desktop → Settings → Capabilities → Add MCP Server"
    echo ""
    echo "  Recommended servers:"
    echo "    AWS Knowledge: https://knowledge-mcp.global.api.aws"
    echo "    PubMed: https://pubmed.mcp.claude.com/mcp"
    echo "    Open Targets: https://mcp.platform.opentargets.org/mcp"
    ;;
  5) # Cursor
    if [ "$SCOPE" = "1" ]; then
      mkdir -p .cursor
      cp "$SCRIPT_DIR/claude-code/.mcp.json" .cursor/mcp.json
      echo "  Copied MCP config to .cursor/mcp.json"
    else
      mkdir -p ~/.cursor
      cp "$SCRIPT_DIR/claude-code/.mcp.json" ~/.cursor/mcp.json
      echo "  Copied MCP config to ~/.cursor/mcp.json"
    fi
    ;;
  *)
    echo "Invalid selection."
    exit 1
    ;;
esac

echo ""
echo "Setup complete."
echo ""
echo "Additional MCP servers (biomedical databases, ontologies) are available in:"
echo "  $REPO_DIR/mcp-servers/"
echo ""
echo "For AWS infrastructure skills, also install the AWS Agent Toolkit:"
echo "  https://github.com/aws/agent-toolkit-for-aws"
