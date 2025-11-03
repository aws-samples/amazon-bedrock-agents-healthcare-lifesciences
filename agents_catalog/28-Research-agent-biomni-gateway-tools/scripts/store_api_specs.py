#!/usr/bin/env python3
"""Store API specifications in SSM parameters for CloudFormation gateway deployment."""

import json
import boto3
import sys
from pathlib import Path

def store_api_spec(file_path: str, ssm_param_name: str):
    """Store API spec file content in SSM parameter."""
    try:
        # Read API spec file
        with open(file_path, 'r') as f:
            api_spec = json.load(f)
        
        # Convert to JSON string for SSM
        api_spec_json = json.dumps(api_spec)
        
        # Store in SSM
        ssm = boto3.client('ssm')
        ssm.put_parameter(
            Name=ssm_param_name,
            Value=api_spec_json,
            Type='String',
            Overwrite=True,
            Description=f'API specification for {file_path}'
        )
        
        print(f"✅ Stored {file_path} in SSM parameter {ssm_param_name}")
        
    except Exception as e:
        print(f"❌ Error storing {file_path}: {str(e)}")
        sys.exit(1)

def main():
    """Store both API specs in SSM parameters."""
    # Database API spec
    db_api_file = "prerequisite/lambda/api_spec.json"
    db_ssm_param = "/app/researchapp/agentcore/db_api_spec"
    
    # Literature API spec  
    lit_api_file = "prerequisite/lambda-literature/api_spec.json"
    lit_ssm_param = "/app/researchapp/agentcore/lit_api_spec"
    
    # Check files exist
    if not Path(db_api_file).exists():
        print(f"❌ Database API spec file not found: {db_api_file}")
        sys.exit(1)
        
    if not Path(lit_api_file).exists():
        print(f"❌ Literature API spec file not found: {lit_api_file}")
        sys.exit(1)
    
    # Store both specs
    store_api_spec(db_api_file, db_ssm_param)
    store_api_spec(lit_api_file, lit_ssm_param)
    
    print("🎉 All API specifications stored successfully")

if __name__ == "__main__":
    main()
