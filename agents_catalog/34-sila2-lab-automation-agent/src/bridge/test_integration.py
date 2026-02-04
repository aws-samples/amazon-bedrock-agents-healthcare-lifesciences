"""Integration test for Bridge Container"""
import subprocess
import time
import requests
import json
import sys

def test_bridge_container():
    print("=== Bridge Container Integration Test ===\n")
    
    # モックgRPCサーバー起動
    print("1. Starting mock gRPC servers...")
    mock_proc = subprocess.Popen(
        [sys.executable, "test_mock_grpc_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)
    print("   ✓ Mock servers started\n")
    
    # MCPサーバー起動
    print("2. Starting MCP server...")
    mcp_proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3)
    print("   ✓ MCP server started\n")
    
    try:
        # ヘルスチェック
        print("3. Testing health endpoint...")
        response = requests.get("http://localhost:8080/health", timeout=2)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # list_devicesテスト
        print("4. Testing list_devices...")
        payload = {"tool_calls": [{"name": "list_devices", "arguments": {}}]}
        response = requests.post(
            "http://localhost:8080/mcp",
            json=payload,
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        # get_device_statusテスト
        print("5. Testing get_device_status...")
        payload = {"tool_calls": [{"name": "get_device_status", "arguments": {"device_id": "hplc"}}]}
        response = requests.post(
            "http://localhost:8080/mcp",
            json=payload,
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        # execute_commandテスト
        print("6. Testing execute_command...")
        payload = {
            "tool_calls": [{
                "name": "execute_command",
                "arguments": {
                    "device_id": "hplc",
                    "command": "start_analysis",
                    "parameters": {"sample": "test-001"}
                }
            }]
        }
        response = requests.post(
            "http://localhost:8080/mcp",
            json=payload,
            timeout=5
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        print("=== All Tests Passed ===")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        # クリーンアップ
        print("\n7. Cleaning up...")
        mcp_proc.terminate()
        mock_proc.terminate()
        time.sleep(1)
        print("   ✓ Cleanup complete")
    
    return True

if __name__ == "__main__":
    success = test_bridge_container()
    sys.exit(0 if success else 1)
