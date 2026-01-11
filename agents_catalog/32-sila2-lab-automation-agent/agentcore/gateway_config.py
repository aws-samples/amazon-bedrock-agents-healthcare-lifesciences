#!/usr/bin/env python3
import boto3
import os
import sys

def register_gateway_tools():
    """Register Lambda Tools to AgentCore Gateway"""
    
    region = os.environ.get('AWS_REGION', 'us-west-2')
    account_id = boto3.client('sts').get_caller_identity()['Account']
    
    tools = [
        {
            'name': 'analyze_heating_rate',
            'description': 'Calculate heating rate from device history data',
            'lambda_arn': f'arn:aws:lambda:{region}:{account_id}:function:sila2-analyze-heating-rate'
        },
        {
            'name': 'execute_autonomous_control',
            'description': 'Execute autonomous control action via MCP',
            'lambda_arn': f'arn:aws:lambda:{region}:{account_id}:function:sila2-execute-autonomous-control'
        }
    ]
    
    bedrock = boto3.client('bedrock-agent-runtime', region_name=region)
    
    print("Registering Gateway Tools...")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['lambda_arn']}")
    
    print("\n✓ Gateway Tools configuration ready")
    print("Note: Actual registration requires AgentCore Gateway API")
    return tools

if __name__ == '__main__':
    register_gateway_tools()
