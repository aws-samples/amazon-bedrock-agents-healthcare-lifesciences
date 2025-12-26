import json
import os
import requests

BRIDGE_URL = os.environ.get('BRIDGE_URL', 'http://172.31.44.121:8080')

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")
    
    # SNSイベントの場合
    if 'Records' in event and event['Records'][0].get('EventSource') == 'aws:sns':
        return handle_sns_event(event)
    
    action = event.get('action')
    
    if action == 'periodic':
        return handle_periodic(event)
    elif action == 'get_history':
        return handle_get_history(event)
    
    print(f"Unknown action: {action}")
    return {"statusCode": 400, "body": json.dumps({"error": "Unknown action"})}

def handle_periodic(event):
    """EventBridgeからの定期実行"""
    devices = event.get('devices', ['hplc'])
    print(f"Periodic collection for devices: {devices}")
    
    results = []
    for device_id in devices:
        try:
            response = requests.get(
                f"{BRIDGE_URL}/api/history/{device_id}",
                params={"minutes": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"Device {device_id}: {data['count']} data points")
                results.append({"device_id": device_id, "status": "success", "count": data['count']})
            else:
                print(f"Device {device_id}: Failed with status {response.status_code}")
                results.append({"device_id": device_id, "status": "error", "code": response.status_code})
        except Exception as e:
            print(f"Device {device_id}: Exception {str(e)}")
            results.append({"device_id": device_id, "status": "error", "error": str(e)})
    
    return {"statusCode": 200, "body": json.dumps({"results": results})}

def handle_get_history(event):
    """Streamlit UIからの履歴取得"""
    device_id = event.get('device_id', 'hplc')
    minutes = event.get('minutes', 5)
    
    try:
        response = requests.get(
            f"{BRIDGE_URL}/api/history/{device_id}",
            params={"minutes": minutes},
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                "statusCode": 200,
                "body": json.dumps(response.json())
            }
        else:
            return {
                "statusCode": response.status_code,
                "body": json.dumps({"error": f"Bridge Server returned {response.status_code}"})
            }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def handle_sns_event(event):
    """SNSからのイベント通知処理"""
    for record in event['Records']:
        sns_message = json.loads(record['Sns']['Message'])
        device_id = sns_message.get('device_id')
        event_type = sns_message.get('event_type')
        value = sns_message.get('value')
        timestamp = sns_message.get('timestamp')
        
        print(f"[SNS EVENT] Device: {device_id}, Type: {event_type}, Value: {value}, Time: {timestamp}")
    
    return {"statusCode": 200, "body": json.dumps({"message": "Event processed"})}
