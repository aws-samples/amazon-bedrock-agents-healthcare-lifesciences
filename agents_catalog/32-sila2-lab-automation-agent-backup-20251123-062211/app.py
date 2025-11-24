from bedrock_agentcore import BedrockAgentCoreApp
import json
import os
import urllib.request
import urllib.parse
import re

app = BedrockAgentCoreApp()

def list_available_devices() -> str:
    """利用可能なSiLA2デバイス一覧を取得"""
    try:
        api_url = os.environ.get('API_GATEWAY_URL', 'https://demo-api-url')
        data = json.dumps({"action": "list"}).encode('utf-8')
        req = urllib.request.Request(f"{api_url}/devices", data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            devices = result.get('devices', [])
            device_list = [f"{d.get('device_id', 'unknown')} ({d.get('status', 'unknown')})" for d in devices]
            return f"利用可能なSiLA2デバイス: {', '.join(device_list)}"
    except Exception as e:
        return f"利用可能なSiLA2デバイス: HPLC-01, CENTRIFUGE-01, PIPETTE-01 (デモ - エラー: {str(e)})"

def get_device_status(device_id: str) -> str:
    """指定デバイスのステータス取得"""
    try:
        api_url = os.environ.get('API_GATEWAY_URL', 'https://demo-api-url')
        data = json.dumps({"action": "status", "device_id": device_id}).encode('utf-8')
        req = urllib.request.Request(f"{api_url}/devices", data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            status = result.get('status', 'unknown')
            temp = result.get('temperature', 'N/A')
            return f"デバイス {device_id} ステータス: {status}, 温度: {temp}°C"
    except Exception as e:
        return f"デバイス {device_id} ステータス: ready (デモ - エラー: {str(e)})"

def execute_device_command(device_id: str, command: str) -> str:
    """デバイスコマンド実行"""
    try:
        api_url = os.environ.get('API_GATEWAY_URL', 'https://demo-api-url')
        data = json.dumps({"action": "command", "device_id": device_id, "command": command}).encode('utf-8')
        req = urllib.request.Request(f"{api_url}/devices", data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            cmd_result = result.get('result', 'completed')
            return f"コマンド '{command}' を {device_id} で実行: {cmd_result}"
    except Exception as e:
        return f"コマンド '{command}' を {device_id} で実行 (デモ - エラー: {str(e)})"

# ツール登録
@app.tool(
    name="list_available_devices",
    description="利用可能なSiLA2デバイス一覧を取得します"
)
def tool_list_available_devices():
    return list_available_devices()

@app.tool(
    name="get_device_status", 
    description="指定されたSiLA2デバイスのステータスを取得します"
)
def tool_get_device_status(device_id: str):
    return get_device_status(device_id)

@app.tool(
    name="execute_device_command",
    description="指定されたSiLA2デバイスでコマンドを実行します"
)
def tool_execute_device_command(device_id: str, command: str):
    return execute_device_command(device_id, command)

if __name__ == "__main__":
    app.run()