#!/usr/bin/env python3
"""
Test client for deployed OLS MCP Server on AgentCore Runtime.

This script tests the deployed OLS MCP server by listing available tools
and invoking them with sample queries.
"""

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from ols_utils import get_access_token, get_ssm_parameter, get_aws_region


async def test_mcp_server(stack_name: str = "terminology-agent"):
    """
    Test the deployed OLS MCP server.

    Args:
        stack_name: CDK stack name (default: terminology-agent)
    """
    print("=" * 80)
    print("🧪 Testing OLS MCP Server")
    print("=" * 80)

    region = get_aws_region()
    print(f"\n📍 AWS Region: {region}")

    # Get configuration from SSM
    print("\n🔍 Retrieving MCP server configuration...")
    try:
        agent_arn = get_ssm_parameter(f"/{stack_name}/ols-mcp-server/agent-arn")
        mcp_url = get_ssm_parameter(f"/{stack_name}/ols-mcp-server/mcp-url")
        print(f"✓ Agent ARN: {agent_arn}")
        print(f"✓ MCP URL: {mcp_url}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Have you deployed the OLS MCP server?")
        print("   Run: python deploy_ols_mcp_server.py")
        sys.exit(1)

    # Get access token
    print("\n🔐 Getting access token...")
    try:
        bearer_token = get_access_token(stack_name)
        print("✓ Access token retrieved")
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        sys.exit(1)

    # Configure headers
    headers = {"authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"}

    # Connect to MCP server
    print(f"\n🔌 Connecting to MCP server...")
    print(f"   URL: {mcp_url}")

    try:
        async with streamablehttp_client(
            mcp_url, headers, timeout=timedelta(seconds=120), terminate_on_close=False
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize session
                print("\n🔄 Initializing MCP session...")
                await session.initialize()
                print("✓ MCP session initialized")

                # List available tools
                print("\n📋 Listing available tools...")
                tool_result = await session.list_tools()

                print("\n" + "=" * 80)
                print("🔧 Available MCP Tools:")
                print("=" * 80)
                for tool in tool_result.tools:
                    print(f"\n• {tool.name}")
                    print(f"  Description: {tool.description}")
                    if hasattr(tool, "inputSchema") and tool.inputSchema:
                        properties = tool.inputSchema.get("properties", {})
                        if properties:
                            print(f"  Parameters: {', '.join(properties.keys())}")

                print(f"\n✅ Found {len(tool_result.tools)} tools available")

                # Test tools
                print("\n" + "=" * 80)
                print("🧪 Testing MCP Tools:")
                print("=" * 80)

                # Test 1: Search for "myocardial infarction"
                print("\n1️⃣ Testing search_terms('myocardial infarction')...")
                try:
                    result = await session.call_tool(
                        name="search_terms", arguments={"query": "myocardial infarction", "rows": 5}
                    )
                    print(f"   ✓ Result: {result.content[0].text[:200]}...")
                except Exception as e:
                    print(f"   ❌ Error: {e}")

                # Test 2: Get ontology info for MONDO
                print("\n2️⃣ Testing get_ontology_info('mondo')...")
                try:
                    result = await session.call_tool(
                        name="get_ontology_info", arguments={"ontology_id": "mondo"}
                    )
                    print(f"   ✓ Result: {result.content[0].text[:200]}...")
                except Exception as e:
                    print(f"   ❌ Error: {e}")

                # Test 3: Search ontologies for "disease"
                print("\n3️⃣ Testing search_ontologies('disease')...")
                try:
                    result = await session.call_tool(
                        name="search_ontologies", arguments={"search": "disease", "size": 3}
                    )
                    print(f"   ✓ Result: {result.content[0].text[:200]}...")
                except Exception as e:
                    print(f"   ❌ Error: {e}")

                # Test 4: Search for diabetes
                print("\n4️⃣ Testing search_terms('diabetes')...")
                try:
                    result = await session.call_tool(
                        name="search_terms",
                        arguments={"query": "diabetes", "ontology": "mondo", "rows": 3},
                    )
                    print(f"   ✓ Result: {result.content[0].text[:200]}...")
                except Exception as e:
                    print(f"   ❌ Error: {e}")

                print("\n" + "=" * 80)
                print("✅ MCP Server Testing Complete!")
                print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error connecting to MCP server: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test deployed OLS MCP Server")
    parser.add_argument(
        "--stack-name",
        default="terminology-agent",
        help="CDK stack name (default: terminology-agent)",
    )

    args = parser.parse_args()

    # Check if required packages are installed
    try:
        import mcp
    except ImportError:
        print("\n❌ ERROR: mcp package is not installed")
        print("\n📦 Please install development dependencies:")
        print("   pip install -r requirements-dev.txt")
        print("\n   Or install mcp individually:")
        print("   pip install mcp")
        sys.exit(1)

    asyncio.run(test_mcp_server(args.stack_name))
