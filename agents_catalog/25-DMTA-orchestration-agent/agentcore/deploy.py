#!/usr/bin/env python3
"""Deploy an AgentCore agent using the agentcore CLI.

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

import subprocess
import sys

import click


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and stream output."""
    result = subprocess.run(cmd, capture_output=False, text=True)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview what will be deployed without deploying")
@click.option("--verbose", "-v", is_flag=True, help="Show resource-level events during deploy")
@click.option("--target", default=None, help="Deploy target (e.g., staging, production)")
def deploy(dry_run, verbose, target):
    """Deploy this agent to AgentCore using the agentcore CLI."""

    # Verify agentcore CLI is installed
    result = subprocess.run(["agentcore", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        click.echo("Error: agentcore CLI not found. Install with: npm install -g @aws/agentcore")
        sys.exit(1)
    click.echo(f"Using agentcore CLI {result.stdout.strip()}")

    # Validate config
    click.echo("\n[1/3] Validating configuration...")
    _run(["agentcore", "validate"], check=False)

    if dry_run:
        click.echo("\n[2/3] Dry run — previewing deployment...")
        _run(["agentcore", "deploy", "--dry-run"])
        return

    # Deploy
    click.echo("\n[2/3] Deploying...")
    cmd = ["agentcore", "deploy", "-y"]
    if verbose:
        cmd.append("-v")
    if target:
        cmd.extend(["--target", target])
    _run(cmd)

    # Status check
    click.echo("\n[3/3] Checking status...")
    _run(["agentcore", "status"])

    click.echo("\n✅ Deployment complete!")


if __name__ == "__main__":
    deploy()
