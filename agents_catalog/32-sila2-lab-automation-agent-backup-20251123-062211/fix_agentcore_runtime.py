#!/usr/bin/env python3
"""
AgentCore Runtime修正スクリプト
404エラーの原因を特定し、修正を適用
"""

import json
import os
import urllib.request
import urllib.parse
import re

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
        return f"利用可能なSiLA2デバイス: HPLC-01, CENTRIFUGE-01, PIPETTE-01 (デモモード: {str(e)})"

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
        return f"デバイス {device_id} ステータス: ready (デモモード: {str(e)})"

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
        return f"コマンド '{command}' を {device_id} で実行 (デモモード: {str(e)})"

def parse_user_message(content: str):
    """ユーザーメッセージを解析してツール呼び出しを判定"""
    content_lower = content.lower()
    
    if "デバイス" in content and ("一覧" in content or "リスト" in content or "利用可能" in content):
        return "list_available_devices", {}
    
    if "ステータス" in content or "状態" in content:
        device_match = re.search(r'(HPLC-\d+|CENTRIFUGE-\d+|PIPETTE-\d+)', content, re.IGNORECASE)
        device_id = device_match.group(1) if device_match else "HPLC-01"
        return "get_device_status", {"device_id": device_id}
    
    if "コマンド" in content or "実行" in content:
        device_match = re.search(r'(HPLC-\d+|CENTRIFUGE-\d+|PIPETTE-\d+)', content, re.IGNORECASE)
        command_match = re.search(r'(start_analysis|stop|reset|calibrate)', content, re.IGNORECASE)
        device_id = device_match.group(1) if device_match else "HPLC-01"
        command = command_match.group(1) if command_match else "start_analysis"
        return "execute_device_command", {"device_id": device_id, "command": command}
    
    return "list_available_devices", {}

def lambda_handler(event, context):
    """AgentCore Runtime用Lambda handler - 修正版"""
    try:
        print(f"[DEBUG] Received event: {json.dumps(event, ensure_ascii=False)}")
        print(f"[DEBUG] Context: {context}")
        
        # 複数の形式のイベントに対応
        tool_name = None
        parameters = {}
        user_message = ""
        
        if isinstance(event, dict):
            # MCP形式
            if 'tool_name' in event:
                tool_name = event.get('tool_name')
                parameters = event.get('parameters', {})
                print(f"[DEBUG] MCP format detected: {tool_name}")
            
            # AgentCore形式 - メッセージベース
            elif 'messages' in event:
                messages = event.get('messages', [])
                if messages and isinstance(messages, list):
                    user_message = messages[-1].get('content', '') if messages[-1] else ''
                    tool_name, parameters = parse_user_message(user_message)
                    print(f"[DEBUG] Messages format detected: {user_message}")
                else:
                    tool_name, parameters = 'list_available_devices', {}
            
            # 直接メッセージ形式
            elif 'message' in event:
                user_message = str(event.get('message', ''))
                tool_name, parameters = parse_user_message(user_message)
                print(f"[DEBUG] Direct message format detected: {user_message}")
            
            # inputText形式
            elif 'inputText' in event:
                user_message = str(event.get('inputText', ''))
                tool_name, parameters = parse_user_message(user_message)
                print(f"[DEBUG] InputText format detected: {user_message}")
            
            # body形式（API Gateway経由）
            elif 'body' in event:
                try:
                    body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
                    if 'message' in body:
                        user_message = str(body.get('message', ''))
                        tool_name, parameters = parse_user_message(user_message)
                        print(f"[DEBUG] Body message format detected: {user_message}")
                    else:
                        tool_name, parameters = 'list_available_devices', {}
                except:
                    tool_name, parameters = 'list_available_devices', {}
            
            # デフォルト
            else:
                tool_name, parameters = 'list_available_devices', {}
                print(f"[DEBUG] Default format used")
        
        else:
            tool_name, parameters = 'list_available_devices', {}
            print(f"[DEBUG] Non-dict event, using default")
        
        print(f"[DEBUG] Processing tool: {tool_name} with parameters: {parameters}")
        
        # ツール実行
        if tool_name == 'list_available_devices':
            result = list_available_devices()
        elif tool_name == 'get_device_status':
            device_id = parameters.get('device_id', 'HPLC-01')
            result = get_device_status(device_id)
        elif tool_name == 'execute_device_command':
            device_id = parameters.get('device_id', 'HPLC-01')
            command = parameters.get('command', 'start_analysis')
            result = execute_device_command(device_id, command)
        else:
            result = list_available_devices()
        
        print(f"[DEBUG] Tool result: {result}")
        
        # AgentCore Runtime用のレスポンス形式
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'response': {'text': result},
                'tool_name': tool_name,
                'parameters': parameters,
                'success': True
            }, ensure_ascii=False)
        }
        
        print(f"[DEBUG] Returning response: {json.dumps(response, ensure_ascii=False)}")
        return response
        
    except Exception as e:
        print(f"[ERROR] Lambda handler error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'response': {'text': f'SiLA2エージェントエラー: {str(e)}'},
                'error': str(e),
                'success': False
            }, ensure_ascii=False)
        }

# テスト用のローカル実行
if __name__ == "__main__":
    # テストイベント
    test_events = [
        {"message": "利用可能なSiLA2デバイスを一覧表示してください"},
        {"inputText": "HPLC-01のステータスを確認してください"},
        {"messages": [{"content": "HPLC-01でstart_analysisコマンドを実行してください"}]},
        {"tool_name": "list_available_devices", "parameters": {}}
    ]
    
    for i, event in enumerate(test_events):
        print(f"\n=== Test {i+1} ===")
        result = lambda_handler(event, None)
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")