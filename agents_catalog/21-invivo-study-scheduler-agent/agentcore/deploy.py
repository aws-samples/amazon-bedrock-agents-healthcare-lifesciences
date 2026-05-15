#!/usr/bin/env python3
"""Deploy an AgentCore agent using the bedrock-agentcore-starter-toolkit.

Usage:
    cd agents_catalog/<agent>/agentcore/
    python deploy.py

    # Or specify a custom agent name:
    python deploy.py --agent my-agent-name

Requires:
    pip install bedrock-agentcore-starter-toolkit click
"""

import time
import sys
from pathlib import Path

import click
from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session


def get_agent_name_from_config() -> str:
    """Read agent name from .bedrock_agentcore.yaml if it exists (redeployment)."""
    config = Path(".bedrock_agentcore.yaml")
    if not config.exists():
        return None
    for line in config.read_text().splitlines():
        line = line.strip()
        if line.startswith("name:") and not line.startswith("name: null"):
            return line.split(":", 1)[1].strip()
    return None


def get_agent_name_from_pyproject() -> str:
    """Read agent name from pyproject.toml [project] name field."""
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return None
    for line in pyproject.read_text().splitlines():
        if line.strip().startswith("name"):
            # Parse: name = "agent-name"
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


@click.command()
@click.option("--agent", default=None, help="Agent name (default: read from pyproject.toml)")
@click.option("--region", default=None, help="AWS region (default: from boto3 session)")
@click.option("--entrypoint", default="main.py", help="Entrypoint file (default: main.py)")
def deploy(agent, region, entrypoint):
    """Configure, build, and deploy an agent to AgentCore."""
    if not agent:
        agent = get_agent_name_from_config() or get_agent_name_from_pyproject()
    if not agent:
        click.echo("Error: could not determine agent name. Use --agent or add [project] name to pyproject.toml")
        sys.exit(1)

    # Normalize name for AgentCore (underscores, no special chars, must start with letter)
    agent_name = agent.replace("-", "_").replace(" ", "_")
    if agent_name[0].isdigit():
        agent_name = "agent_" + agent_name

    if not region:
        region = Session().region_name or "us-east-1"

    click.echo(f"Deploying agent: {agent_name}")
    click.echo(f"Region: {region}")
    click.echo(f"Entrypoint: {entrypoint}")

    runtime = Runtime()

    click.echo("\n[1/3] Configuring...")
    runtime.configure(
        entrypoint=entrypoint,
        agent_name=agent_name,
        region=region,
        auto_create_execution_role=True,
        auto_create_ecr=True,
    )

    click.echo("[2/3] Launching (building container + deploying)...")
    runtime.launch()

    click.echo("[3/3] Waiting for READY status...")
    end_states = {"READY", "CREATE_FAILED", "DELETE_FAILED", "UPDATE_FAILED"}

    status_response = runtime.status()
    status = status_response.endpoint["status"]

    while status not in end_states:
        time.sleep(10)
        status_response = runtime.status()
        status = status_response.endpoint["status"]
        click.echo(f"  Status: {status}")

    if status == "READY":
        click.echo(f"\n✅ Agent '{agent_name}' deployed successfully!")
    else:
        click.echo(f"\n❌ Deployment failed with status: {status}")
        sys.exit(1)


if __name__ == "__main__":
    deploy()
