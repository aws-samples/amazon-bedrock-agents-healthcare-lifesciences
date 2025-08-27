#!/usr/bin/env python3
"""
Test the /query endpoint with IAM authentication
"""
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json
from load_deployment_info import get_lambda_function_url

def test_query_endpoint():
    """Test the /query endpoint with signed request"""
    
    # Get Lambda Function URL from deployment info
    base_url = get_lambda_function_url()
    if not base_url:
        raise ValueError("Lambda Function URL not found in deployment_info.txt")
    
    url = f"{base_url}/query"
    
    # Create AWS session with default profile
    session = boto3.Session(profile_name='default')
    credentials = session.get_credentials()
    
    # Prepare the query
    query_data = json.dumps({"question": "What is the enrollment status"})
    
    print("🧪 Testing /query endpoint with IAM authentication")
    print(f"URL: {url}")
    print(f"Question: What is the enrollment status")
    print()
    
    # Create signed POST request
    request = AWSRequest(method='POST', url=url, data=query_data)
    request.headers['Content-Type'] = 'application/json'
    SigV4Auth(credentials, 'lambda', 'us-west-2').add_auth(request)
    
    try:
        # Make the request
        response = requests.post(url, headers=dict(request.headers), data=query_data)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Query endpoint test: SUCCESS")
            print()
            
            # Extract the agent response
            agent_response = result.get('answer', 'No answer field found')
            
            print("📋 Agent Response:")
            print("=" * 60)
            print(agent_response)
            print("=" * 60)
            
            # Show success status
            success = result.get('success', False)
            error = result.get('error')
            print(f"\nℹ️ Success: {success}")
            if error:
                print(f"⚠️ Error: {error}")
            else:
                print("✅ No errors reported")
        else:
            print("❌ Query endpoint test: FAILED")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Query endpoint test: ERROR")
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    test_query_endpoint()