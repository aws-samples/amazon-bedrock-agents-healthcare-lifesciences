#!/usr/bin/env python3
"""Phase 3 Simple統合テスト"""

import json
import sys
import os

def test_mock_device():
    """Mock Device Lambda直接テスト"""
    print("🧪 Mock Device Lambda テスト")
    
    from unified_mock_device_lambda import lambda_handler as mock_handler
    
    # リストテスト
    result = mock_handler({'action': 'list'}, {})
    print(f"  List: {result['statusCode']} - {json.loads(result['body'])}")
    
    # ステータステスト
    result = mock_handler({'action': 'status', 'device_id': 'HPLC-01'}, {})
    print(f"  Status: {result['statusCode']} - {json.loads(result['body'])}")
    
    # コマンドテスト
    result = mock_handler({'action': 'command', 'device_id': 'HPLC-01', 'command': 'start'}, {})
    print(f"  Command: {result['statusCode']} - {json.loads(result['body'])}")

def test_protocol_bridge():
    """Protocol Bridge Lambda直接テスト"""
    print("🌉 Protocol Bridge Lambda テスト")
    
    from protocol_bridge_lambda import lambda_handler as bridge_handler
    
    # Mock Device gRPC URL設定
    os.environ['MOCK_DEVICE_GRPC_URL'] = 'http://localhost:8080'
    
    # リストテスト
    result = bridge_handler({'action': 'list'}, {})
    print(f"  List: {result['statusCode']} - {json.loads(result['body'])}")
    
    # ステータステスト
    result = bridge_handler({'action': 'status', 'device_id': 'HPLC-01'}, {})
    print(f"  Status: {result['statusCode']} - {json.loads(result['body'])}")

def test_agentcore_runtime():
    """AgentCore Runtime テスト"""
    print("🤖 AgentCore Runtime テスト")
    
    from main_agentcore_phase3_simple import lambda_handler as runtime_handler
    
    # Protocol Bridge URL設定
    os.environ['PROTOCOL_BRIDGE_URL'] = 'http://localhost:8080'
    
    # リストテスト
    result = runtime_handler({'tool_name': 'list_available_devices'}, {})
    print(f"  List: {result['statusCode']} - {json.loads(result['body'])}")
    
    # ステータステスト
    result = runtime_handler({'tool_name': 'get_device_status', 'parameters': {'device_id': 'HPLC-01'}}, {})
    print(f"  Status: {result['statusCode']} - {json.loads(result['body'])}")
    
    # コマンドテスト
    result = runtime_handler({'tool_name': 'execute_device_command', 'parameters': {'device_id': 'HPLC-01', 'command': 'start'}}, {})
    print(f"  Command: {result['statusCode']} - {json.loads(result['body'])}")

def main():
    print("🎯 Phase 3 Simple 統合テスト開始")
    print("=" * 50)
    
    try:
        test_mock_device()
        print()
        test_protocol_bridge()
        print()
        test_agentcore_runtime()
        print()
        print("✅ 全テスト完了")
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()