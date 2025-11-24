import json
import requests
import os

def parse_event_body(event):
    """イベントボディ解析ヘルパー関数"""
    body = {}
    if 'body' in event and event['body']:
        if isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event['body']
    return body

def handle_http_to_grpc(event, context):
    """HTTP → gRPC変換処理"""
    body = parse_event_body(event)
    
    action = body.get('action', event.get('action', 'list'))
    device_id = body.get('device_id', event.get('device_id', 'HPLC-01'))
    command = body.get('command', event.get('command', 'status'))
    
    mock_device_grpc_url = os.environ.get('MOCK_DEVICE_GRPC_URL', 'https://demo-grpc-url')
    
    try:
        grpc_request = {
            'grpc_method': 'SiLA2Device',
            'action': action,
            'device_id': device_id,
            'command': command,
            'protocol': 'grpc'
        }
        
        response = requests.post(
            f"{mock_device_grpc_url}/grpc",
            json=grpc_request,
            timeout=10
        )
        
        if response.status_code == 200:
            grpc_response = response.json()
            response_data = {
                'bridge_status': 'success',
                'protocol_conversion': 'http_to_grpc_completed',
                'grpc_method': 'SiLA2Device',
                'data': grpc_response
            }
        else:
            response_data = {
                'bridge_status': 'error',
                'protocol_conversion': 'grpc_failed',
                'error': f'gRPC HTTP {response.status_code}'
            }
            
    except Exception:
        if action == 'list':
            fallback_data = {
                'devices': [
                    {'device_id': 'HPLC-01', 'status': 'ready'},
                    {'device_id': 'CENTRIFUGE-01', 'status': 'ready'}
                ]
            }
        elif action == 'status':
            fallback_data = {'device_id': device_id, 'status': 'ready'}
        else:
            fallback_data = {'device_id': device_id, 'result': 'success'}
        
        response_data = {
            'bridge_status': 'fallback',
            'protocol_conversion': 'grpc_fallback',
            'data': fallback_data
        }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(response_data)
    }

def handle_grpc_to_http(event, context):
    """gRPC → HTTP変換処理"""
    body = parse_event_body(event)
    
    grpc_method = body.get('grpc_method', 'SiLA2Device')
    action = body.get('action', 'list')
    device_id = body.get('device_id', 'HPLC-01')
    command = body.get('command', 'status')
    
    http_request = {
        'action': action,
        'device_id': device_id,
        'command': command
    }
    
    response_data = {
        'bridge_status': 'success',
        'protocol_conversion': 'grpc_to_http_completed',
        'http_method': 'POST',
        'data': http_request
    }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(response_data)
    }

def lambda_handler(event, context):
    """Protocol Bridge Lambda - HTTP/gRPC双方向変換"""
    try:
        path = event.get('path', '')
        
        if '/grpc-bridge' in path:
            return handle_grpc_to_http(event, context)
        else:
            return handle_http_to_grpc(event, context)
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'bridge_status': 'error',
                'protocol_conversion': 'failed',
                'error': str(e)
            })
        }