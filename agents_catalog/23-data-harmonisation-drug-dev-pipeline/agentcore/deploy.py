#!/usr/bin/env python3
"""Deploy an AgentCore agent using the agentcore CLI (@aws/agentcore).

Usage:
    cd agents_catalog/<agent>/agentcore/
    python deploy.py

    # Or with options:
    python deploy.py --dry-run        # Preview what will be deployed
    python deploy.py --verbose        # Show resource-level events

Prerequisites:
    npm install -g @aws/agentcore    # Install agentcore CLI (>= 0.9.0)

See: https://github.com/aws/agent-toolkit-for-aws/blob/main/plugins/aws-agents/skills/agents-deploy/SKILL.md
"""

import shutil
import subprocess
import sys

import click


def _find_agentcore_cli() -> str:
    """Find the new @aws/agentcore CLI (Node.js), not the deprecated Python starter toolkit."""
    # Try npx first (always works if npm is installed)
    npx = shutil.which("npx")
    if npx:
        return "npx @aws/agentcore"

    # Try direct binary
    cli = shutil.which("agentcore")
    if cli:
        # Verify it's the Node.js version (>= 0.9.0), not the Python one
        result = subprocess.run([cli, "--version"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip().replace(".", "").isdigit():
            return cli

    return None


def _run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and stream output."""
    result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview what will be deployed without deploying")
@click.option("--verbose", "-v", is_flag=True, help="Show resource-level events during deploy")
@click.option("--target", default=None, help="Deploy target (e.g., staging, production)")
def deploy(dry_run, verbose, target):
    """Deploy this agent to AgentCore using the agentcore CLI."""

    cli = _find_agentcore_cli()
    if not cli:
        click.echo("Error: agentcore CLI not found. Install with: npm install -g @aws/agentcore")
        sys.exit(1)

    # Verify version
    result = subprocess.run(f"{cli} --version", shell=True, capture_output=True, text=True)
    click.echo(f"Using agentcore CLI v{result.stdout.strip()}")

    # Validate config
    click.echo("\n[1/3] Validating configuration...")
    _run(f"{cli} validate", check=False)

    if dry_run:
        click.echo("\n[2/3] Dry run — previewing deployment...")
        _run(f"{cli} deploy --dry-run")
        return

    # Deploy
    click.echo("\n[2/3] Deploying...")
    cmd = f"{cli} deploy -y"
    if verbose:
        cmd += " -v"
    if target:
        cmd += f" --target {target}"
    _run(cmd)

    # Status check
    click.echo("\n[3/3] Checking status...")
    _run(f"{cli} status")

    click.echo("\n✅ Deployment complete!")


if __name__ == "__main__":
    deploy()
