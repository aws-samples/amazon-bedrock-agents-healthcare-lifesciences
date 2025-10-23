#!/usr/bin/env python3

import boto3
import json
import uuid
import click
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.utils import get_ssm_parameter

@click.command()
@click.option("--agent-name", "-a", required=True, help="Agent name to test")
@click.option("--prompt", "-p", required=True, help="Prompt to send to the agent")
@click.option("--session-id", "-s", help="Session ID (generates random if not provided)")
def test_agent(agent_name, prompt, session_id):
    """Test deployed agent using IAM authentication."""
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Initialize the Bedrock AgentCore client
    agent_core_client = boto3.client('bedrock-agentcore')
    agent_core_control_client = boto3.client('bedrock-agentcore-control')
    
    # Get agent ARN using list_agent_runtimes
    try:
        response = agent_core_control_client.list_agent_runtimes(maxResults=100)
        agent_arn = None
        
        for runtime in response.get('agentRuntimes', []):
            if runtime.get('agentRuntimeName') == agent_name:
                agent_arn = runtime.get('agentRuntimeArn')
                break
        
        if not agent_arn:
            print(f"❌ Agent '{agent_name}' not found in runtime list")
            return
            
    except Exception as e:
        print(f"❌ Failed to list agent runtimes: {e}")
        return
    
    print(f"🤖 Testing agent: {agent_name}")
    print(f"📝 Prompt: {prompt}")
    print(f"🔗 Session ID: {session_id}")
    print(f"🎯 Agent ARN: {agent_arn}")
    print("=" * 60)
    
    # Initialize the Bedrock AgentCore client
    agent_core_client = boto3.client('bedrock-agentcore')
    
    # Prepare the payload
    payload = json.dumps({"prompt": prompt}).encode()
    
    try:
        # Invoke the agent
        response = agent_core_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            runtimeSessionId=session_id,
            payload=payload
        )
        
        # Process and print the response
        if "text/event-stream" in response.get("contentType", ""):
            # Handle streaming response
            print("📡 Streaming response:")
            content = []
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                        print(line, end="", flush=True)
                        content.append(line)
            print("\n" + "=" * 60)
            print("✅ Response completed")

        elif response.get("contentType") == "application/json":
            # Handle standard JSON response
            content = []
            for chunk in response.get("response", []):
                content.append(chunk.decode('utf-8'))
            result = json.loads(''.join(content))
            print("📄 JSON response:")
            print(json.dumps(result, indent=2))
        
        else:
            # Print raw response for other content types
            print("📋 Raw response:")
            print(response)
            
    except Exception as e:
        print(f"❌ Error invoking agent: {e}")

if __name__ == "__main__":
    test_agent()
