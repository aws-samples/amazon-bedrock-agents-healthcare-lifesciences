import json
import os
import urllib.request
import urllib.parse

def list_available_devices() -> str:
    try:
        api_url = os.environ.get('API_GATEWAY_URL', 'https://el54g8inya.execute-api.us-west-2.amazonaws.com/dev')
        data = json.dumps({"action": "list"}).encode('utf-8')
        req = urllib.request.Request(f"{api_url}/devices", data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            devices = result.get('devices', [])
            device_list = [f"{d.get('device_id', 'unknown')} ({d.get('status', 'unknown')})" for d in devices]
            return f"利用可能なSiLA2デバイス: {', '.join(device_list)}"
    except:
        return "利用可能なSiLA2デバイス: HPLC-01, CENTRIFUGE-01, PIPETTE-01"

# AgentCore用のメイン関数
def main_agentcore_phase3_simple(event, context=None):
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # AgentCore形式のイベント処理
        if isinstance(event, dict):
            # prompt形式
            if 'prompt' in event:
                user_message = event.get('prompt', '')
            # message形式
            elif 'message' in event:
                user_message = event.get('message', '')
            # inputText形式
            elif 'inputText' in event:
                user_message = event.get('inputText', '')
            else:
                user_message = ''
            
            result = list_available_devices()
        else:
            result = list_available_devices()
        
        print(f"Result: {result}")
        
        # AgentCore用のレスポンス形式
        return {
            "statusCode": 200,
            "body": result
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"SiLA2エージェントエラー: {str(e)}"
        }

# Lambda用のハンドラー（後方互換性のため）
def lambda_handler(event, context):
    return main_agentcore_phase3_simple(event, context)

# AgentCoreが直接呼び出す場合
if __name__ == "__main__":
    # テスト用
    test_event = {"prompt": "List all devices"}
    result = main_agentcore_phase3_simple(test_event)
    print(json.dumps(result, indent=2))