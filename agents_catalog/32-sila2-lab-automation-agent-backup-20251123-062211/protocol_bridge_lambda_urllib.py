import json
import urllib.request
import urllib.parse

def lambda_handler(event, context):
    try:
        action = event.get('action')
        device_id = event.get('device_id', 'HPLC-01')
        command = event.get('command', 'status')
        
        if action == 'list':
            result = {
                "devices": [
                    {"device_id": "HPLC-01", "status": "ready", "type": "hplc"},
                    {"device_id": "CENTRIFUGE-01", "status": "busy", "type": "centrifuge"},
                    {"device_id": "PIPETTE-01", "status": "ready", "type": "pipette"}
                ]
            }
        elif action == 'status':
            result = {
                "device_id": device_id,
                "status": "ready",
                "temperature": 25.0,
                "protocol": "gRPC"
            }
        elif action == 'command':
            result = {
                "device_id": device_id,
                "command": command,
                "result": f"Command '{command}' executed successfully",
                "status": "completed"
            }
        else:
            result = {"error": "unknown_action", "action": action}
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({"error": f"bridge_error: {str(e)}"})
        }