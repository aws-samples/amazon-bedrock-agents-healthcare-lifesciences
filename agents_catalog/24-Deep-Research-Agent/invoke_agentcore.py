"""
Simple helper function for invoking AgentCore agents from Jupyter notebooks or CLI.

This module provides a simplified interface for testing agents deployed to
Amazon Bedrock AgentCore from within Jupyter notebooks or as a command-line tool.
"""

import argparse
import json
import sys
import uuid
from typing import Dict, Any, Optional

import boto3
import botocore


def invoke_agentcore(
    agent_runtime_name: str,
    prompt: str,
    session_id: Optional[str] = None,
    region_name: Optional[str] = None,
) -> None:
    """
    Invoke an AgentCore agent and stream the response to stdout.

    Args:
        agent_runtime_name: Name of the deployed agent runtime
        prompt: The prompt/question to send to the agent
        session_id: Optional session ID for conversation continuity (auto-generated if not provided)
        region_name: Optional AWS region name (uses default if not provided)

    Example:
        >>> invoke_agentcore(
        ...     agent_runtime_name="my_agent",
        ...     prompt="What is the weather today?"
        ... )
    """
    # Initialize clients
    control_client = boto3.client("bedrock-agentcore-control", region_name=region_name)
    runtime_client = boto3.client(
        "bedrock-agentcore",
        region_name=region_name,
        config=botocore.config.Config(read_timeout=900, connect_timeout=5),
    )

    # Look up agent ARN by name
    print(f"🔍 Looking up agent: {agent_runtime_name}")
    response = control_client.list_agent_runtimes(maxResults=100)

    agent_arn = None
    for agent in response.get("agentRuntimes", []):
        if agent.get("agentRuntimeName") == agent_runtime_name:
            agent_arn = agent.get("agentRuntimeArn")
            break

    if not agent_arn:
        print(f"❌ Agent '{agent_runtime_name}' not found")
        return

    print(f"✅ Found agent: {agent_arn}\n")

    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Prepare payload
    payload = json.dumps({"prompt": prompt}).encode()

    # Invoke agent
    print(f"💬 Sending prompt: {prompt}\n")
    print("=" * 80)

    response = runtime_client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        qualifier="DEFAULT",
        runtimeSessionId=session_id,
        payload=payload,
    )

    # Stream response
    response_stream = response.get("response")
    if response_stream and hasattr(response_stream, "iter_lines"):
        for line in response_stream.iter_lines(chunk_size=1024):
            if line:
                line_str = line.decode("utf-8").strip()
                # Handle Server-Sent Events format
                if line_str.startswith("data: "):
                    data_content = line_str[6:]
                    if data_content and data_content != "[DONE]":
                        # Try to parse as JSON and extract text
                        try:
                            # First parse to get the outer JSON structure
                            json_data = json.loads(data_content)

                            # Handle different response formats
                            if isinstance(json_data, dict):
                                text = (
                                    json_data.get("text")
                                    or json_data.get("content")
                                    or json_data.get("message")
                                )
                                if text:
                                    print(text, end="", flush=True)
                                else:
                                    print(data_content, end="", flush=True)
                            elif isinstance(json_data, str):
                                # The response is a JSON-encoded string, print it directly
                                # This handles the case where text comes as a string value
                                # Add newline after tool usage markers
                                if json_data.startswith("🔧 Using tool:"):
                                    print(json_data, flush=True)
                                else:
                                    print(json_data, end="", flush=True)
                            else:
                                print(data_content, end="", flush=True)
                        except json.JSONDecodeError:
                            # Not valid JSON, print as-is
                            print(data_content, end="", flush=True)

    print("\n" + "=" * 80)
    print(f"✅ Response complete (session: {session_id})")


def main():
    """Command-line interface for invoking AgentCore agents."""
    parser = argparse.ArgumentParser(
        description="Invoke an Amazon Bedrock AgentCore agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Invoke by agent name
  python invoke_agentcore.py --name my_agent --prompt "Hello, agent!"
  
  # Invoke with specific session ID
  python invoke_agentcore.py --name my_agent --prompt "Continue conversation" --session-id abc-123
  
  # Invoke in specific region
  python invoke_agentcore.py --name my_agent --prompt "What can you do?" --region us-west-2
  
  # Interactive mode (read prompt from stdin)
  echo "Tell me about yourself" | python invoke_agentcore.py --name my_agent
        """
    )
    
    parser.add_argument(
        "--name",
        required=True,
        help="Name of the deployed agent runtime"
    )
    
    parser.add_argument(
        "--prompt",
        help="Prompt to send to the agent (if not provided, reads from stdin)"
    )
    
    parser.add_argument(
        "--session-id",
        help="Session ID for conversation continuity (auto-generated if not provided)"
    )
    
    parser.add_argument(
        "--region",
        help="AWS region name (uses default region if not provided)"
    )
    
    args = parser.parse_args()
    
    # Get prompt from argument or stdin
    prompt = args.prompt
    if not prompt:
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()
        else:
            print("Error: --prompt is required when not piping input", file=sys.stderr)
            sys.exit(1)
    
    if not prompt:
        print("Error: Prompt cannot be empty", file=sys.stderr)
        sys.exit(1)
    
    # Invoke the agent
    try:
        invoke_agentcore(
            agent_runtime_name=args.name,
            prompt=prompt,
            session_id=args.session_id,
            region_name=args.region
        )
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
