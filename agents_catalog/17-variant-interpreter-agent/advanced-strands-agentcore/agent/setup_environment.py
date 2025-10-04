#!/usr/bin/env python3
"""
Environment setup for genomics agent
Run this before using main.py independently
"""

import os
import boto3

def setup_environment():
    """Setup required environment variables and AWS configuration"""
    
    # Get AWS configuration
    session = boto3.Session()
    region = session.region_name or 'us-east-1'
    
    try:
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        print(f"✅ AWS Account: {account_id}")
        print(f"✅ Region: {region}")
    except Exception as e:
        print(f"⚠️ Warning: Could not get AWS account info: {e}")
        account_id = "unknown"
    
    # Set environment variables if not already set
    env_vars = {
        'AWS_DEFAULT_REGION': region,
        'REGION': region,
        'ACCOUNT_ID': account_id,
        'VARIANT_STORE_NAME': 'genomicsvariantstore',
        'ANNOTATION_STORE_NAME': 'genomicsannotationstore',
        'LAKE_FORMATION_DATABASE': '<YOUR_AWS_PROFILE>',  # Update this
        'MODEL_ID': 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
    }
    
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = str(value)
            print(f"✅ Set {key}={value}")
    
    print("✅ Environment setup complete")
    return region, account_id

if __name__ == "__main__":
    setup_environment()
