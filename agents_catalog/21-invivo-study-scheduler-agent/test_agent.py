#!/usr/bin/env python3
"""
Test script for the In Vivo Study Scheduler Agent
"""

import boto3
import json
import time
from typing import Dict, Any

def test_invivo_scheduler_agent():
    """Test the In Vivo Study Scheduler Agent with sample data"""
    
    # Initialize Bedrock Runtime client
    client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    
    # Agent details from CloudFormation outputs
    agent_id = "TH1THHQ3EV"
    agent_alias_id = "DDJBKJXA9I"
    
    # Test message
    test_message = """I need to schedule 5 in vivo studies for the next 30 days. Here are the studies:

1. Study A needs 150 animals for 3 days starting preferably on day 5
2. Study B needs 200 animals for 2 days with high priority  
3. Study C needs 100 animals for 1 day
4. Study D needs 300 animals for 4 days starting preferably on day 10
5. Study E needs 80 animals for 2 days with low priority

Our lab can handle a maximum of 500 animals per day. Please optimize the schedule and show me a visualization."""
    
    try:
        print("Testing In Vivo Study Scheduler Agent...")
        print(f"Agent ID: {agent_id}")
        print(f"Agent Alias ID: {agent_alias_id}")
        print(f"Test Message: {test_message}")
        print("-" * 80)
        
        # Invoke the agent
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=f"test-session-{int(time.time())}",
            inputText=test_message
        )
        
        # Process the response stream
        print("Agent Response:")
        print("-" * 40)
        
        full_response = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    print(chunk_text, end='')
                    full_response += chunk_text
        
        print("\n" + "-" * 80)
        print("Test completed successfully!")
        
        return full_response
        
    except Exception as e:
        print(f"Error testing agent: {str(e)}")
        return None

if __name__ == "__main__":
    test_invivo_scheduler_agent()
