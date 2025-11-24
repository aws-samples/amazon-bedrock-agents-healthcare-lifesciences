#!/usr/bin/env python3
import json
import subprocess
import sys

def test_layer_1_agentcore_runtime():
    """Layer 1: AgentCore Runtime テスト"""
    print("🔍 Layer 1: AgentCore Runtime テスト")
    
    cmd = [
        "aws", "lambda", "invoke",
        "--function-name", "sila2-agentcore-runtime-dev",
        "--payload", '{"tool_name":"list_available_devices","parameters":{}}',
        "--region", "us-west-2",
        "layer1_response.json"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        with open("layer1_response.json", "r") as f:
            response = json.load(f)
        print(f"✅ Layer 1 成功: {response}")
        return True
    else:
        print(f"❌ Layer 1 失敗: {result.stderr}")
        return False

def test_layer_2_api_gateway():
    """Layer 2: API Gateway テスト"""
    print("🔍 Layer 2: API Gateway テスト")
    
    cmd = [
        "curl", "-X", "POST",
        "https://el54g8inya.execute-api.us-west-2.amazonaws.com/dev/devices",
        "-H", "Content-Type: application/json",
        "-d", '{"action":"list"}',
        "--max-time", "5"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        response = json.loads(result.stdout)
        print(f"✅ Layer 2 成功: {response}")
        return True
    else:
        print(f"❌ Layer 2 失敗: {result.stderr}")
        return False

def test_layer_3_protocol_bridge():
    """Layer 3: Protocol Bridge テスト"""
    print("🔍 Layer 3: Protocol Bridge テスト")
    
    cmd = [
        "aws", "lambda", "invoke",
        "--function-name", "sila2-protocol-bridge-dev",
        "--payload", '{"action":"status","device_id":"HPLC-01"}',
        "--region", "us-west-2",
        "layer3_response.json"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        with open("layer3_response.json", "r") as f:
            response = json.load(f)
        print(f"✅ Layer 3 成功: {response}")
        return True
    else:
        print(f"❌ Layer 3 失敗: {result.stderr}")
        return False

def test_layer_4_mock_devices():
    """Layer 4: Mock Devices テスト"""
    print("🔍 Layer 4: Mock Devices テスト")
    
    cmd = [
        "aws", "lambda", "invoke",
        "--function-name", "sila2-mock-device-lambda-dev",
        "--payload", '{"action":"command","device_id":"PIPETTE-01","command":"start"}',
        "--region", "us-west-2",
        "layer4_response.json"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        with open("layer4_response.json", "r") as f:
            response = json.load(f)
        print(f"✅ Layer 4 成功: {response}")
        return True
    else:
        print(f"❌ Layer 4 失敗: {result.stderr}")
        return False

def main():
    print("🚀 SiLA2 Phase 3 - 4層アーキテクチャ統合テスト開始")
    print("=" * 60)
    
    results = []
    results.append(test_layer_4_mock_devices())
    results.append(test_layer_3_protocol_bridge())
    results.append(test_layer_2_api_gateway())
    results.append(test_layer_1_agentcore_runtime())
    
    print("=" * 60)
    print("📊 テスト結果サマリー:")
    
    layers = ["Layer 4 (Mock Devices)", "Layer 3 (Protocol Bridge)", "Layer 2 (API Gateway)", "Layer 1 (AgentCore Runtime)"]
    for i, (layer, result) in enumerate(zip(layers, results)):
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"  {layer}: {status}")
    
    success_count = sum(results)
    print(f"\n🎯 総合結果: {success_count}/4 層が正常動作")
    
    if success_count == 4:
        print("🎉 Phase 3 完全成功！4層アーキテクチャが正常に動作しています")
        return 0
    else:
        print("⚠️  一部の層で問題が発生しています")
        return 1

if __name__ == "__main__":
    sys.exit(main())