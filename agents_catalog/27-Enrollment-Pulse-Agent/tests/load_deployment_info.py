#!/usr/bin/env python3
"""
Load deployment URLs from deployment_info.txt
"""
import os
from pathlib import Path

def load_deployment_info():
    """Load deployment URLs from backend/deployment_info.txt"""
    # Look for deployment_info.txt in backend directory
    backend_dir = Path(__file__).parent.parent / "backend"
    deployment_file = backend_dir / "deployment_info.txt"
    
    if not deployment_file.exists():
        raise FileNotFoundError(
            f"deployment_info.txt not found at {deployment_file}\n"
            "Please run './deploy_only.sh' in the backend directory first."
        )
    
    urls = {}
    with open(deployment_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    urls[key] = value
    
    return urls

def get_api_gateway_url():
    """Get API Gateway URL from deployment info"""
    urls = load_deployment_info()
    return urls.get('API_GATEWAY_URL')

def get_lambda_function_url():
    """Get Lambda Function URL from deployment info"""
    urls = load_deployment_info()
    return urls.get('LAMBDA_FUNCTION_URL')

if __name__ == "__main__":
    try:
        urls = load_deployment_info()
        print("📋 Deployment URLs:")
        for key, value in urls.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"❌ Error: {e}")