#!/usr/bin/env python3
"""
Cleanup OLS MCP Server deployment.

This script removes the deployed OLS MCP server and cleans up
all associated resources.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ols_utils import get_ssm_parameter, get_aws_region
import boto3


def cleanup_ols_mcp_deployment(
    stack_name: str = "terminology-agent", force: bool = False
) -> bool:
    """
    Cleanup OLS MCP Server deployment.

    Args:
        stack_name: CDK stack name
        force: If True, skip confirmation

    Returns:
        True if cleanup successful
    """
    print("=" * 80)
    print("🗑️  OLS MCP Server Cleanup")
    print("=" * 80)

    region = get_aws_region()
    ssm = boto3.client("ssm")
    agentcore_client = boto3.client("bedrock-agentcore-control", region_name=region)

    # Get deployment info
    try:
        agent_arn = get_ssm_parameter(f"/{stack_name}/ols-mcp-server/agent-arn")
        agent_id = get_ssm_parameter(f"/{stack_name}/ols-mcp-server/agent-id")

        print(f"\n📋 Found deployment:")
        print(f"   Agent ARN: {agent_arn}")
        print(f"   Agent ID:  {agent_id}")
        print(f"   Region:    {region}")

        if not force:
            response = input("\n⚠️  Are you sure you want to delete this? (yes/no): ")
            if response.lower() != "yes":
                print("❌ Cleanup cancelled")
                return False

    except Exception as e:
        print(f"\n⚠️  No deployment found or error: {e}")
        # Try to clean up parameters anyway
        pass

    # Delete AgentCore Runtime
    print("\n🗑️  Deleting AgentCore Runtime...")
    try:
        agentcore_client.delete_runtime(agentRuntimeId=agent_id)
        print("✓ Runtime deleted")
    except agentcore_client.exceptions.ResourceNotFoundException:
        print("⚠️  Runtime not found (may already be deleted)")
    except Exception as e:
        print(f"⚠️  Error deleting runtime: {e}")

    # Delete SSM parameters
    print("\n🗑️  Deleting SSM parameters...")
    parameters = [
        f"/{stack_name}/ols-mcp-server/agent-arn",
        f"/{stack_name}/ols-mcp-server/agent-id",
        f"/{stack_name}/ols-mcp-server/mcp-url",
    ]

    for param in parameters:
        try:
            ssm.delete_parameter(Name=param)
            print(f"✓ Deleted {param}")
        except ssm.exceptions.ParameterNotFound:
            print(f"⚠️  Parameter not found: {param}")
        except Exception as e:
            print(f"⚠️  Error deleting {param}: {e}")

    print("\n" + "=" * 80)
    print("✅ Cleanup Complete!")
    print("=" * 80)
    print("\n💡 To redeploy, run: python deploy_ols_mcp_server.py")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup OLS MCP Server deployment")
    parser.add_argument(
        "--stack-name",
        default="terminology-agent",
        help="CDK stack name (default: terminology-agent)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    try:
        success = cleanup_ols_mcp_deployment(args.stack_name, args.force)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        sys.exit(1)
