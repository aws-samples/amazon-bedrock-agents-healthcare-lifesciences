#!/usr/bin/env python3
"""
Check if OLS MCP Server is deployed.

This module checks for an existing OLS MCP Server deployment by looking
for SSM parameters created during deployment.
"""

import sys
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).parent))

from ols_utils import get_ssm_parameter, get_aws_region


def check_ols_mcp_deployment(stack_name: str = "terminology-agent") -> dict:
    """
    Check if OLS MCP Server is deployed.

    Args:
        stack_name: CDK stack name

    Returns:
        dict with deployment status:
        {
            "deployed": bool,
            "agent_arn": str or None,
            "agent_id": str or None,
            "mcp_url": str or None,
            "status": str
        }
    """
    region = get_aws_region()
    agentcore_client = boto3.client("bedrock-agentcore-control", region_name=region)

    try:
        # Try to get deployment info from SSM
        agent_arn = get_ssm_parameter(f"/{stack_name}/ols-mcp-server/agent-arn")
        agent_id = get_ssm_parameter(f"/{stack_name}/ols-mcp-server/agent-id")
        mcp_url = get_ssm_parameter(f"/{stack_name}/ols-mcp-server/mcp-url")

        # Verify runtime still exists in AgentCore
        try:
            response = agentcore_client.get_runtime(agentRuntimeId=agent_id)
            status = response.get("status", "UNKNOWN")

            return {
                "deployed": True,
                "agent_arn": agent_arn,
                "agent_id": agent_id,
                "mcp_url": mcp_url,
                "status": status,
            }
        except agentcore_client.exceptions.ResourceNotFoundException:
            # SSM parameters exist but runtime was deleted
            return {
                "deployed": False,
                "agent_arn": None,
                "agent_id": None,
                "mcp_url": None,
                "status": "Runtime not found (orphaned SSM parameters)",
            }

    except Exception:
        # No SSM parameters found - not deployed
        return {
            "deployed": False,
            "agent_arn": None,
            "agent_id": None,
            "mcp_url": None,
            "status": "Not deployed",
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Check OLS MCP Server deployment status"
    )
    parser.add_argument(
        "--stack-name",
        default="terminology-agent",
        help="CDK stack name (default: terminology-agent)",
    )

    args = parser.parse_args()

    result = check_ols_mcp_deployment(args.stack_name)

    print(f"\nDeployment Status: {result['status']}")
    if result["deployed"]:
        print(f"Agent ARN: {result['agent_arn']}")
        print(f"Agent ID: {result['agent_id']}")
        print(f"MCP URL: {result['mcp_url']}")
    else:
        print("OLS MCP Server is not deployed")

    sys.exit(0 if result["deployed"] else 1)
