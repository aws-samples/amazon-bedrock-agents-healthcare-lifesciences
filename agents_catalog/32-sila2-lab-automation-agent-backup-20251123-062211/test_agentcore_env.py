#!/usr/bin/env python3
import json
import os

# AgentCore Runtime環境変数テスト用
def test_env_vars():
    api_url = os.environ.get('API_GATEWAY_URL', 'NOT_SET')
    print(f"API_GATEWAY_URL: {api_url}")
    
    # 環境変数一覧
    for key, value in os.environ.items():
        if 'API' in key or 'GATEWAY' in key or 'URL' in key:
            print(f"{key}: {value}")

def lambda_handler(event, context):
    test_env_vars()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'API_GATEWAY_URL': os.environ.get('API_GATEWAY_URL', 'NOT_SET'),
            'event': event
        })
    }

if __name__ == "__main__":
    test_env_vars()