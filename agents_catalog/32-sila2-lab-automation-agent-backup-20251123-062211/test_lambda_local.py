#!/usr/bin/env python3
"""Lambda関数のローカルテスト"""

import json
import os
import sys

def test_mock_device_lambda():
    """Mock Device Lambdaテスト"""
    print("🧪 Mock Device Lambda テスト")
    
    from unified_mock_device_lambda import lambda_handler as mock_handler
    
    # テストケース1: デバイス一覧
    event1 = {'action': 'list'}
    result1 = mock_handler(event1, {})
    print(f"  List: {result1['statusCode']} - {json.loads(result1['body'])}")
    
    # テストケース2: デバイス状態
    event2 = {'action': 'status', 'device_id': 'HPLC-01'}
    result2 = mock_handler(event2, {})
    print(f"  Status: {result2['statusCode']} - {json.loads(result2['body'])}")
    
    # テストケース3: コマンド実行
    event3 = {'action': 'command', 'device_id': 'HPLC-01', 'command': 'start'}
    result3 = mock_handler(event3, {})
    print(f"  Command: {result3['statusCode']} - {json.loads(result3['body'])}")

def test_protocol_bridge_lambda():
    """Protocol Bridge Lambdaテスト"""
    print("\n🌉 Protocol Bridge Lambda テスト")
    
    # 環境変数設定
    os.environ['MOCK_DEVICE_GRPC_URL'] = 'https://demo-grpc-url'
    
    from protocol_bridge_lambda import lambda_handler as bridge_handler
    
    # テストケース1: HTTP → gRPC変換 (デフォルトパス)
    event1 = {
        'path': '/bridge',
        'body': json.dumps({'action': 'list'})
    }
    result1 = bridge_handler(event1, {})
    print(f"  HTTP→gRPC: {result1['statusCode']} - {json.loads(result1['body'])}")
    
    # テストケース2: gRPC → HTTP変換
    event2 = {
        'path': '/grpc-bridge',
        'body': json.dumps({
            'grpc_method': 'SiLA2Device',
            'action': 'status',
            'device_id': 'HPLC-01'
        })
    }
    result2 = bridge_handler(event2, {})
    print(f"  gRPC→HTTP: {result2['statusCode']} - {json.loads(result2['body'])}")
    
    # テストケース3: フォールバック
    event3 = {
        'path': '/bridge',
        'body': json.dumps({'action': 'status', 'device_id': 'CENTRIFUGE-01'})
    }
    result3 = bridge_handler(event3, {})
    print(f"  Fallback: {result3['statusCode']} - {json.loads(result3['body'])}")

def test_agentcore_runtime_lambda():
    """AgentCore Runtime Lambdaテスト"""
    print("\n🤖 AgentCore Runtime Lambda テスト")
    
    # 環境変数設定
    os.environ['PROTOCOL_BRIDGE_URL'] = 'https://demo-bridge-url'
    
    from main_agentcore_phase3_simple import lambda_handler as runtime_handler
    
    # テストケース1: デバイス一覧
    event1 = {'tool_name': 'list_available_devices'}
    result1 = runtime_handler(event1, {})
    print(f"  List: {result1['statusCode']} - {json.loads(result1['body'])}")
    
    # テストケース2: デバイス状態
    event2 = {
        'tool_name': 'get_device_status',
        'parameters': {'device_id': 'HPLC-01'}
    }
    result2 = runtime_handler(event2, {})
    print(f"  Status: {result2['statusCode']} - {json.loads(result2['body'])}")
    
    # テストケース3: コマンド実行
    event3 = {
        'tool_name': 'execute_device_command',
        'parameters': {'device_id': 'HPLC-01', 'command': 'start'}
    }
    result3 = runtime_handler(event3, {})
    print(f"  Command: {result3['statusCode']} - {json.loads(result3['body'])}")

def test_integration():
    """統合テスト"""
    print("\n🔗 統合テスト")
    
    # Mock Device → Protocol Bridge → AgentCore Runtime
    print("  Mock Device → Protocol Bridge → AgentCore Runtime")
    
    # 1. Mock Deviceテスト
    from unified_mock_device_lambda import lambda_handler as mock_handler
    mock_result = mock_handler({'action': 'list'}, {})
    print(f"    Mock Device: ✅ {mock_result['statusCode']}")
    
    # 2. Protocol Bridgeテスト
    os.environ['MOCK_DEVICE_GRPC_URL'] = 'https://demo-grpc-url'
    from protocol_bridge_lambda import lambda_handler as bridge_handler
    bridge_result = bridge_handler({'path': '/bridge', 'body': '{"action": "list"}'}, {})
    print(f"    Protocol Bridge: ✅ {bridge_result['statusCode']}")
    
    # 3. AgentCore Runtimeテスト
    os.environ['PROTOCOL_BRIDGE_URL'] = 'https://demo-bridge-url'
    from main_agentcore_phase3_simple import lambda_handler as runtime_handler
    runtime_result = runtime_handler({'tool_name': 'list_available_devices'}, {})
    print(f"    AgentCore Runtime: ✅ {runtime_result['statusCode']}")

def main():
    print("🎯 Lambda関数ローカルテスト開始")
    print("=" * 50)
    
    try:
        test_mock_device_lambda()
        test_protocol_bridge_lambda()
        test_agentcore_runtime_lambda()
        test_integration()
        
        print("\n✅ 全テスト完了")
        
    except Exception as e:
        print(f"\n❌ テストエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()