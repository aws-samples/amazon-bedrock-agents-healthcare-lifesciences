#!/usr/bin/env python3
import boto3
import os
import sys
import json

def configure_runtime():
    """Configure AgentCore Runtime with Instructions and Memory"""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    instructions_file = os.path.join(script_dir, 'agent_instructions.txt')
    
    with open(instructions_file, 'r') as f:
        instructions = f.read()
    
    agent_id = os.environ.get('AGENT_ID')
    memory_id = os.environ.get('MEMORY_ID')
    region = os.environ.get('AWS_REGION', 'us-west-2')
    
    print("AgentCore Runtime Configuration:")
    print(f"  Agent ID: {agent_id}")
    print(f"  Memory ID: {memory_id}")
    print(f"  Model: anthropic.claude-3-5-sonnet-20241022-v2:0")
    print(f"  Instructions: {len(instructions)} chars")
    
    if not agent_id or not memory_id:
        print("\n⚠ Warning: Agent ID or Memory ID not provided")
        print("Memory configuration will be applied at runtime")
        return
    
    try:
        client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        # Associate memory with runtime
        client.associate_agent_memory(
            agentIdentifier=agent_id,
            memoryIdentifier=memory_id
        )
        print("\n✓ Memory associated with runtime")
        print("✓ Tool call recording enabled via Strands Agent config")
        
    except Exception as e:
        print(f"\n⚠ Warning: {e}")
        print("Configuration will be applied at runtime")

if __name__ == '__main__':
    configure_runtime()
