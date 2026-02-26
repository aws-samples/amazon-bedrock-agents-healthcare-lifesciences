#!/usr/bin/env python3
"""
Deploy OLS (Ontology Lookup Service) MCP Server to Amazon Bedrock AgentCore Runtime.

This script deploys the EBI OLS MCP server to AgentCore Runtime using the existing
Cognito authentication from the Terminology Agent stack.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

import boto3

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ols_utils import (
    get_terminology_agent_cognito_config,
    put_ssm_parameter,
    get_aws_region,
)
from check_ols_mcp_deployment import check_ols_mcp_deployment

# Try to import bedrock_agentcore_starter_toolkit
try:
    from bedrock_agentcore_starter_toolkit import Runtime
except ImportError:
    print("❌ bedrock_agentcore_starter_toolkit not found")
    print("📦 Installing bedrock_agentcore_starter_toolkit...")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "bedrock-agentcore-starter-toolkit",
        ]
    )
    from bedrock_agentcore_starter_toolkit import Runtime


def check_ols_mcp_server(ols_source_path: Path) -> bool:
    """Check if OLS MCP server source code exists."""
    server_file = ols_source_path / "src" / "ols_mcp_server" / "server.py"
    return server_file.exists()


def clone_ols_repository(dest_path: Path, repo_url: str = "https://github.com/seandavi/ols-mcp-server.git") -> None:
    """
    Clone OLS MCP server repository from GitHub.

    Creates structure: dest_path/ols/src/ols_mcp_server/
    This matches the notebook's expected structure.

    Args:
        dest_path: Destination directory for deployment
        repo_url: Git repository URL for OLS MCP server
    """
    print(f"📥 Cloning OLS MCP server from {repo_url}")

    # Create destination directory
    dest_path.mkdir(parents=True, exist_ok=True)

    # Clone destination
    ols_dest = dest_path / "ols"

    # Remove existing if present
    if ols_dest.exists():
        shutil.rmtree(ols_dest)

    # Clone the repository
    subprocess.check_call(
        ["git", "clone", "--quiet", repo_url, str(ols_dest)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print("✓ Repository cloned")


def patch_ols_for_agentcore(dest_path: Path) -> None:
    """
    Patch OLS MCP server code for AgentCore Runtime compatibility.

    AgentCore Runtime requires:
    - host="0.0.0.0" and stateless_http=True for FastMCP initialization
    - transport="streamable-http" for mcp.run() calls
    """
    print("🔧 Patching OLS server for AgentCore Runtime...")

    server_file = dest_path / "ols" / "src" / "ols_mcp_server" / "server.py"

    with open(server_file, "r") as f:
        content = f.read()

    # Patch 1: Update FastMCP initialization to use stateless HTTP
    original_init = 'mcp = FastMCP("OLS MCP Server")'
    patched_init = '''mcp = FastMCP(host="0.0.0.0", stateless_http=True)  # AgentCore Runtime'''

    if original_init in content:
        content = content.replace(original_init, patched_init)
        print("  ✓ Patched FastMCP initialization for stateless HTTP")
    else:
        print("  ⚠️  FastMCP initialization pattern not found")

    # Patch 2: Update all mcp.run() calls to use streamable-http transport
    original_run = "    mcp.run()"
    patched_run = '    mcp.run(transport="streamable-http")  # AgentCore Runtime'

    if original_run in content:
        content = content.replace(original_run, patched_run)
        print("  ✓ Patched mcp.run() calls for streamable-http transport")
    else:
        print("  ⚠️  mcp.run() pattern not found")

    with open(server_file, "w") as f:
        f.write(content)

    print("✓ AgentCore Runtime patches applied")


def generate_requirements_file(ols_source_path: Path, dest_path: Path) -> Path:
    """Generate requirements.txt from pyproject.toml using uv."""
    print("📝 Generating requirements.txt...")

    pyproject_file = ols_source_path / "pyproject.toml"
    requirements_file = dest_path / "requirements.txt"

    # Check if uv is installed
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ uv not found. Installing uv...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "uv"])

    # Create constraint file to pin fastmcp to 2.x during compilation
    # This ensures uv resolves compatible versions of all dependencies together
    constraint_file = dest_path / "constraints.txt"
    with open(constraint_file, "w") as f:
        f.write("# Constraint for AgentCore Runtime - FastMCP 2.x required for stateless HTTP\n")
        f.write("fastmcp>=2.10.5,<3.0.0\n")

    # Generate requirements.txt with constraints
    subprocess.check_call(
        [
            "uv",
            "pip",
            "compile",
            str(pyproject_file),
            "--constraint",
            str(constraint_file),
            "--output-file",
            str(requirements_file),
        ]
    )

    # Add boto3 for OpenTelemetry instrumentation
    with open(requirements_file, "a") as f:
        f.write("\n# AWS SDK for OpenTelemetry instrumentation\n")
        f.write("boto3>=1.35.0\n")

    print(f"✓ Requirements file generated: {requirements_file}")
    return requirements_file


def deploy_ols_mcp_server(
    stack_name: str = "terminology-agent",
    tool_name: str = "ols_mcp_server",
    force_redeploy: bool = False,
) -> dict:
    """
    Deploy OLS MCP server to AgentCore Runtime.

    Args:
        stack_name: CDK stack name (default: terminology-agent)
        tool_name: Name for the deployed MCP server
        force_redeploy: If True, redeploy even if already exists

    Returns:
        dict with agent_arn, agent_id, and mcp_url
    """
    print("=" * 80)
    print("🚀 Deploying OLS MCP Server to AgentCore Runtime")
    print("=" * 80)

    region = get_aws_region()
    print(f"\n📍 AWS Region: {region}")

    # Check if already deployed
    print("\n🔍 Checking for existing deployment...")
    existing = check_ols_mcp_deployment(stack_name)

    if existing.get("deployed"):
        if not force_redeploy:
            print("\n✅ OLS MCP Server is already deployed!")
            print(f"   Agent ARN: {existing['agent_arn']}")
            print(f"   Status: {existing['status']}")
            print("\n💡 To redeploy, use --force-redeploy flag")
            print("   Or cleanup first: python cleanup_ols_mcp.py")
            return {
                "agent_arn": existing["agent_arn"],
                "agent_id": existing["agent_id"],
                "mcp_url": existing["mcp_url"],
                "already_deployed": True,
            }
        else:
            print("⚠️  Force redeploy requested. Cleaning up existing deployment...")
            from cleanup_ols_mcp import cleanup_ols_mcp_deployment

            cleanup_ols_mcp_deployment(stack_name, force=True)
            print("✓ Cleanup complete. Proceeding with deployment...\n")

    # Create deployment directory
    deploy_dir = Path(__file__).parent / "ols_mcp_deployment"
    deploy_dir.mkdir(exist_ok=True)

    # Clone OLS MCP server from GitHub
    clone_ols_repository(deploy_dir)

    # Patch for AgentCore Runtime compatibility
    patch_ols_for_agentcore(deploy_dir)

    # Generate requirements.txt from cloned repo
    ols_cloned_path = deploy_dir / "ols"
    requirements_file = generate_requirements_file(ols_cloned_path, deploy_dir)

    # Verify required files (matching notebook structure)
    required_files = [
        deploy_dir / "ols" / "src" / "ols_mcp_server" / "server.py",
        deploy_dir / "ols" / "src" / "ols_mcp_server" / "models.py",
        deploy_dir / "ols" / "src" / "ols_mcp_server" / "__init__.py",
        requirements_file,
    ]

    print("\n🔍 Verifying required files...")
    for file in required_files:
        if not file.exists():
            print(f"❌ Required file not found: {file}")
            sys.exit(1)
        print(f"✓ {file.name}")

    # Get Cognito configuration
    print("\n🔐 Configuring Cognito authentication...")
    cognito_config = get_terminology_agent_cognito_config(stack_name)

    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [cognito_config["client_id"]],
            "discoveryUrl": cognito_config["discovery_url"],
        }
    }

    # Change to deployment directory BEFORE configuring
    # This ensures the Dockerfile and .dockerignore are created in the right place
    original_dir = os.getcwd()
    os.chdir(deploy_dir)

    # Configure AgentCore Runtime
    print("\n⚙️  Configuring AgentCore Runtime...")
    agentcore_runtime = Runtime()

    response = agentcore_runtime.configure(
        entrypoint="ols/src/ols_mcp_server/server.py",  # Match notebook structure
        auto_create_execution_role=True,
        auto_create_ecr=True,
        requirements_file="requirements.txt",  # At root level
        region=region,
        authorizer_configuration=auth_config,
        protocol="MCP",
        agent_name=tool_name,
    )
    print("✓ Configuration completed")

    # Launch to AgentCore Runtime
    print("\n🚀 Launching MCP server to AgentCore Runtime...")
    print("   This may take several minutes...")

    launch_result = agentcore_runtime.launch(auto_update_on_conflict=True)

    print("✓ Launch completed")
    print(f"\n📋 Agent ARN: {launch_result.agent_arn}")
    print(f"📋 Agent ID: {launch_result.agent_id}")

    # Construct MCP URL
    encoded_arn = launch_result.agent_arn.replace(":", "%3A").replace("/", "%2F")
    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

    # Store configuration in SSM
    print("\n💾 Storing configuration in Parameter Store...")
    put_ssm_parameter(
        f"/{stack_name}/ols-mcp-server/agent-arn",
        launch_result.agent_arn,
        description="OLS MCP Server Agent ARN",
    )
    put_ssm_parameter(
        f"/{stack_name}/ols-mcp-server/agent-id",
        launch_result.agent_id,
        description="OLS MCP Server Agent ID",
    )
    put_ssm_parameter(
        f"/{stack_name}/ols-mcp-server/mcp-url",
        mcp_url,
        description="OLS MCP Server URL",
    )

    print("✓ Configuration stored")

    # Change back to original directory
    os.chdir(original_dir)

    print("\n" + "=" * 80)
    print("✅ OLS MCP Server Deployment Complete!")
    print("=" * 80)
    print(f"\n📍 Agent ARN: {launch_result.agent_arn}")
    print(f"📍 Agent ID: {launch_result.agent_id}")
    print(f"📍 MCP URL: {mcp_url}")
    print(f"\n💡 Test the deployment with: python test_ols_client.py")

    return {
        "agent_arn": launch_result.agent_arn,
        "agent_id": launch_result.agent_id,
        "mcp_url": mcp_url,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Deploy OLS MCP Server to AgentCore Runtime"
    )
    parser.add_argument(
        "--stack-name",
        default="terminology-agent",
        help="CDK stack name (default: terminology-agent)",
    )
    parser.add_argument(
        "--tool-name",
        default="ols_mcp_server",
        help="Name for the deployed MCP server (default: ols_mcp_server)",
    )
    parser.add_argument(
        "--force-redeploy",
        action="store_true",
        help="Force redeployment even if already exists",
    )

    args = parser.parse_args()

    try:
        result = deploy_ols_mcp_server(
            stack_name=args.stack_name,
            tool_name=args.tool_name,
            force_redeploy=args.force_redeploy,
        )
    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        sys.exit(1)
