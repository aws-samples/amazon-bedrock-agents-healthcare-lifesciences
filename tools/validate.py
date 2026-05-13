#!/usr/bin/env python3
"""Validate HCLS Agents Toolkit structure: marketplace manifests, plugin configs, skills, and MCP configs."""

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ERRORS = []
WARNINGS = []

KEBAB_CASE = re.compile(r"^[a-z][a-z0-9]+(-[a-z0-9]+)*$")


def error(msg: str):
    ERRORS.append(msg)
    print(f"  ERROR: {msg}")


def warn(msg: str):
    WARNINGS.append(msg)
    print(f"  WARN:  {msg}")


def validate_json(path: Path):
    if not path.exists():
        error(f"Missing file: {path.relative_to(REPO_ROOT)}")
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        error(f"Invalid JSON in {path.relative_to(REPO_ROOT)}: {e}")
        return None


def validate_marketplace_manifests():
    print("\n[Marketplace Manifests]")

    # Claude Code marketplace
    data = validate_json(REPO_ROOT / ".claude-plugin" / "marketplace.json")
    if data:
        if "name" not in data:
            error(".claude-plugin/marketplace.json missing 'name'")
        if "plugins" not in data or not data["plugins"]:
            error(".claude-plugin/marketplace.json missing 'plugins'")
        else:
            for plugin in data["plugins"]:
                source = plugin.get("source", "")
                if source and not (REPO_ROOT / source.lstrip("./")).exists():
                    error(f"Plugin source path does not exist: {source}")

    # Codex marketplace
    data = validate_json(REPO_ROOT / ".agents" / "plugins" / "marketplace.json")
    if data:
        if "name" not in data:
            error(".agents/plugins/marketplace.json missing 'name'")
        if "plugins" not in data or not data["plugins"]:
            error(".agents/plugins/marketplace.json missing 'plugins'")


def validate_plugin_manifests():
    print("\n[Plugin Manifests]")

    # Claude Code plugin
    data = validate_json(REPO_ROOT / "plugins" / "hcls-agents" / ".claude-plugin" / "plugin.json")
    if data:
        if "name" not in data:
            error("Claude plugin.json missing 'name'")

    # Codex plugin
    data = validate_json(REPO_ROOT / "plugins" / "hcls-agents" / ".codex-plugin" / "plugin.json")
    if data:
        for field in ("name", "version", "description", "author"):
            if field not in data:
                error(f"Codex plugin.json missing '{field}'")
        if "interface" not in data:
            warn("Codex plugin.json missing 'interface' block")


def validate_mcp_configs():
    print("\n[MCP Configurations]")

    for mcp_file in REPO_ROOT.rglob(".mcp.json"):
        rel = mcp_file.relative_to(REPO_ROOT)
        data = validate_json(mcp_file)
        if not data:
            continue
        servers = data.get("mcpServers", {})
        if not servers:
            warn(f"{rel}: no mcpServers defined")
            continue
        if isinstance(servers, str):
            continue  # MCPB binary URL format
        for name, config in servers.items():
            if isinstance(config, str):
                continue  # MCPB binary URL
            if isinstance(config, dict):
                has_command = "command" in config
                has_url = "url" in config
                has_type = "type" in config
                if not has_command and not has_url:
                    error(f"{rel}: server '{name}' has neither 'command' nor 'url'")


def validate_skills():
    print("\n[Skills]")

    skills_dir = REPO_ROOT / "skills"
    if not skills_dir.exists():
        error("skills/ directory missing")
        return

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            warn(f"skills/{skill_dir.name}/SKILL.md missing")
            continue

        content = skill_md.read_text()
        if not content.startswith("---"):
            error(f"skills/{skill_dir.name}/SKILL.md missing YAML frontmatter")
            continue

        # Extract frontmatter
        parts = content.split("---", 2)
        if len(parts) < 3:
            error(f"skills/{skill_dir.name}/SKILL.md malformed frontmatter")
            continue

        frontmatter = parts[1].strip()
        has_name = any(line.startswith("name:") for line in frontmatter.splitlines())
        has_desc = any(line.startswith("description:") for line in frontmatter.splitlines())

        if not has_name:
            error(f"skills/{skill_dir.name}/SKILL.md frontmatter missing 'name'")
        if not has_desc:
            error(f"skills/{skill_dir.name}/SKILL.md frontmatter missing 'description'")

        # Validate name is kebab-case
        if has_name:
            for line in frontmatter.splitlines():
                if line.startswith("name:"):
                    name_val = line.split(":", 1)[1].strip()
                    if not KEBAB_CASE.match(name_val):
                        error(f"skills/{skill_dir.name}/SKILL.md name '{name_val}' is not kebab-case")


def validate_platform_configs():
    print("\n[Platform Configs]")

    platforms_dir = REPO_ROOT / "platforms"
    expected = ["claude-code", "kiro", "codex", "q-desktop"]
    for platform in expected:
        pdir = platforms_dir / platform
        if not pdir.exists():
            error(f"platforms/{platform}/ directory missing")
        elif not (pdir / "README.md").exists():
            warn(f"platforms/{platform}/README.md missing")

    setup = platforms_dir / "setup.sh"
    if not setup.exists():
        error("platforms/setup.sh missing")
    elif not os.access(setup, os.X_OK):
        warn("platforms/setup.sh is not executable")


def main():
    print("Validating HCLS Agents Toolkit structure...")

    validate_marketplace_manifests()
    validate_plugin_manifests()
    validate_mcp_configs()
    validate_skills()
    validate_platform_configs()

    print(f"\n{'='*50}")
    print(f"Errors: {len(ERRORS)}, Warnings: {len(WARNINGS)}")

    if ERRORS:
        print("\nValidation FAILED.")
        sys.exit(1)
    else:
        print("\nValidation PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
