#!/usr/bin/env python3
"""Verify Phase 7 AgentCore Setup"""
import boto3
import os
import sys

def verify_lambda_functions():
    """Verify Phase 7 Lambda functions exist"""
    region = os.environ.get('AWS_REGION', 'us-west-2')
    lambda_client = boto3.client('lambda', region_name=region)
    
    required_functions = [
        'sila2-analyze-heating-rate',
        'sila2-agentcore-invoker'
    ]
    
    print("Verifying Lambda Functions...")
    all_exist = True
    
    for func_name in required_functions:
        try:
            lambda_client.get_function(FunctionName=func_name)
            print(f"  ✓ {func_name}")
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"  ✗ {func_name} - NOT FOUND")
            all_exist = False
        except Exception as e:
            print(f"  ⚠ {func_name} - Error: {e}")
            all_exist = False
    
    return all_exist

def verify_agent_files():
    """Verify required configuration files exist"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    required_files = [
        'agent_instructions.txt',
        'gateway_config.py',
        'runtime_config.py'
    ]
    
    print("\nVerifying Configuration Files...")
    all_exist = True
    
    for filename in required_files:
        filepath = os.path.join(script_dir, filename)
        if os.path.exists(filepath):
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} - NOT FOUND")
            all_exist = False
    
    return all_exist

def verify_agent_ids():
    """Verify Agent ID and Alias ID are available"""
    print("\nVerifying Agent IDs...")
    
    agent_id_file = '/tmp/agent_id.txt'
    alias_id_file = '/tmp/alias_id.txt'
    
    agent_exists = os.path.exists(agent_id_file)
    alias_exists = os.path.exists(alias_id_file)
    
    if agent_exists:
        with open(agent_id_file, 'r') as f:
            agent_id = f.read().strip()
        print(f"  ✓ Agent ID: {agent_id}")
    else:
        print(f"  ✗ Agent ID file not found")
    
    if alias_exists:
        with open(alias_id_file, 'r') as f:
            alias_id = f.read().strip()
        print(f"  ✓ Alias ID: {alias_id}")
    else:
        print(f"  ✗ Alias ID file not found")
    
    return agent_exists and alias_exists

def main():
    """Run all verification checks"""
    print("=== Phase 7 Setup Verification ===\n")
    
    lambda_ok = verify_lambda_functions()
    files_ok = verify_agent_files()
    ids_ok = verify_agent_ids()
    
    print("\n=== Verification Summary ===")
    print(f"Lambda Functions: {'✓ PASS' if lambda_ok else '✗ FAIL'}")
    print(f"Configuration Files: {'✓ PASS' if files_ok else '✗ FAIL'}")
    print(f"Agent IDs: {'✓ PASS' if ids_ok else '✗ FAIL'}")
    
    if lambda_ok and files_ok and ids_ok:
        print("\n✓ All checks passed - Phase 7 setup complete")
        return 0
    else:
        print("\n⚠ Some checks failed - review errors above")
        return 1

if __name__ == '__main__':
    sys.exit(main())
