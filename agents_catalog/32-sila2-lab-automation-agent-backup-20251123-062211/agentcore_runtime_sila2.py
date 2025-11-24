import json
import os
import urllib.request
import urllib.parse
import urllib.error

def list_available_devices() -> str:
    """利用可能なSiLA2デバイス一覧を取得"""
    try:
        api_url = os.environ.get('API_GATEWAY_URL')
        data = json.dumps({"action": "list"}).encode('utf-8')
        
        req = urllib.request.Request(
            f"{api_url}/devices",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                devices = result.get('devices', [])
                device_list = []
                for d in devices:
                    if isinstance(d, dict):
                        device_list.append(d.get('device_id', str(d)))
                    else:
                        device_list.append(str(d))
                return f"利用可能なSiLA2デバイス: {', '.join(device_list)}"
            else:
                return "デモSiLA2デバイス: HPLC-01, CENTRIFUGE-01, PIPETTE-01"
    except Exception as e:
        return f"デモSiLA2デバイス: HPLC-01, CENTRIFUGE-01, PIPETTE-01 (AWS接続エラー: {str(e)})"

def get_device_status(device_id: str) -> str:
    """指定デバイスのステータス取得"""
    try:
        api_url = os.environ.get('API_GATEWAY_URL')
        data = json.dumps({"action": "status", "device_id": device_id}).encode('utf-8')
        
        req = urllib.request.Request(
            f"{api_url}/devices",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                status = result.get('status', 'unknown')
                return f"デバイス {device_id} のステータス: {status}"
            else:
                return f"デバイス {device_id} のステータス: ready (デモ)"
    except Exception as e:
        return f"デバイス {device_id} のステータス: ready (デモ - AWS接続エラー: {str(e)})"

def execute_device_command(device_id: str, command: str) -> str:
    """デバイスコマンド実行"""
    try:
        api_url = os.environ.get('API_GATEWAY_URL')
        data = json.dumps({"action": "command", "device_id": device_id, "command": command}).encode('utf-8')
        
        req = urllib.request.Request(
            f"{api_url}/devices",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                res = result.get('result', 'success')
                return f"デバイス {device_id} でコマンド '{command}' を実行: {res}"
            else:
                return f"デバイス {device_id} でコマンド '{command}' を実行: success (デモ)"
    except Exception as e:
        return f"デバイス {device_id} でコマンド '{command}' を実行: success (デモ - AWS接続エラー: {str(e)})"

def lambda_handler(event, context):
    """AgentCore Runtime用Lambda handler"""
    try:
        # MCP形式のイベント処理
        tool_name = event.get('tool_name')
        parameters = event.get('parameters', {})
        
        if tool_name == 'list_available_devices':
            result = list_available_devices()
        elif tool_name == 'get_device_status':
            device_id = parameters.get('device_id', '')
            result = get_device_status(device_id)
        elif tool_name == 'execute_device_command':
            device_id = parameters.get('device_id', '')
            command = parameters.get('command', '')
            result = execute_device_command(device_id, command)
        else:
            result = f"未知のツール: {tool_name}"
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'result': result,
                'tool_name': tool_name,
                'parameters': parameters
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'tool_name': event.get('tool_name', 'unknown')
            })
        }
