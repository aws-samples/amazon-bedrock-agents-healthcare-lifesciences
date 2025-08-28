#!/usr/bin/env python3
"""
Test API Gateway endpoints (no authentication required)
"""
import requests
import json
from load_deployment_info import get_api_gateway_url

def test_api_gateway_endpoints():
    """Test public API Gateway endpoints"""
    
    # Get API Gateway URL from deployment info
    base_url = get_api_gateway_url()
    if not base_url:
        raise ValueError("API Gateway URL not found in deployment_info.txt")
    
    print("🧪 Testing API Gateway endpoints")
    print(f"Base URL: {base_url}")
    print()
    
    # Test endpoints
    endpoints = [
        "/status/overall",
        "/sites/performance", 
        "/sites/underperforming"
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"Testing: {endpoint}")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint}: SUCCESS")
                print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else f'{len(data)} items'}")
            else:
                print(f"❌ {endpoint}: FAILED ({response.status_code})")
                print(f"   Error: {response.text[:100]}...")
                
        except Exception as e:
            print(f"❌ {endpoint}: ERROR - {str(e)}")
        
        print()
    
    # Test query endpoint
    print("Testing: /query (sync)")
    try:
        query_data = {"question": "What is the current enrollment status?"}
        response = requests.post(f"{base_url}/query", json=query_data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ /query: SUCCESS")
            print(f"   Success: {result.get('success', False)}")
            if result.get('answer'):
                print(f"   Answer length: {len(result['answer'])} characters")
        else:
            print(f"❌ /query: FAILED ({response.status_code})")
            print(f"   Error: {response.text[:100]}...")
            
    except Exception as e:
        print(f"❌ /query: ERROR - {str(e)}")

if __name__ == "__main__":
    test_api_gateway_endpoints()