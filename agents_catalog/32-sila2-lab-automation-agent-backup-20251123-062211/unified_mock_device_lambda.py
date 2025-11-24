import json

def lambda_handler(event, context):
    """AWS Lambda handler - Phase 3 Simple gRPC対応"""
    try:
        # HTTP Bodyからパラメータ取得
        body = {}
        if 'body' in event and event['body']:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        
        # gRPCリクエストかどうか判定
        is_grpc_request = body.get('protocol') == 'grpc' or body.get('grpc_method')
        
        action = body.get('action', event.get('action', 'list'))
        device_id = body.get('device_id', event.get('device_id', 'HPLC-01'))
        command = body.get('command', event.get('command', 'status'))
        
        if action == 'list':
            devices = [
                {"device_id": "HPLC-01", "status": "ready", "type": "hplc"},
                {"device_id": "CENTRIFUGE-01", "status": "busy", "type": "centrifuge"},
                {"device_id": "PIPETTE-01", "status": "ready", "type": "pipette"}
            ]
            response_data = {"devices": devices}
            
        elif action == 'status':
            response_data = {
                "device_id": device_id,
                "status": "ready",
                "temperature": 25.0,
                "timestamp": "2025-01-21T03:00:00Z"
            }
            
        elif action == 'command':
            response_data = {
                "device_id": device_id,
                "command": command,
                "result": f"Command '{command}' executed successfully",
                "status": "completed"
            }
        else:
            response_data = {"error": f"Unknown action: {action}"}
        
        # gRPCリクエストの場合はメタデータ追加
        if is_grpc_request:
            response_data['grpc_method'] = body.get('grpc_method', 'SiLA2Device')
            response_data['protocol'] = 'grpc'
            response_data['sila2_version'] = '2.0'
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
        
    except:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({"error": "device_error"})
        }