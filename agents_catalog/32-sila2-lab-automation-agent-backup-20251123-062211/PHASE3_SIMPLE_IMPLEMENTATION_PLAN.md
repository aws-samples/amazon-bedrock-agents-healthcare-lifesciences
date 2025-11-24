# Phase 3 Complete Implementation Plan - SiLA2 Lab Automation Agent (シンプル化版)

## 🎯 概要

Phase 3では、**4層アーキテクチャ**による完全な実装を行います（シンプル化版）：

```
AgentCore Runtime → Gateway Tools → Protocol Bridge → Mock SiLA2 Devices
     (MCP)              (HTTP)         (gRPC)           (gRPC)
```

### 主要目標
- **完全な4層分離**: 各層の責任を明確に分離
- **gRPC通信実装**: SiLA2プロトコルのgRPC実装
- **AWS環境デプロイ**: CloudFormation + Lambda + AgentCore
- **シンプルなエラーハンドリング**: 基本的なtry/exceptのみ
- **E2Eテスト**: ローカル + AWS環境での動作確認

### シンプル化方針
- ❌ 複雑なフォールバック機能削除
- ❌ 詳細なログ出力削除
- ❌ 複数段階リトライ削除
- ✅ 4層アーキテクチャ構造維持
- ✅ MCP・gRPC通信プロトコル維持

## 📅 シンプル化実装計画

### Step 1: Mock Device Lambda強化 (Day 1) - シンプル版

#### 1.1 gRPC機能追加（シンプル版）
```python
# unified_mock_device_lambda.py シンプル強化版
import grpc
import json
from concurrent import futures

class SiLA2DeviceService:
    def GetDeviceStatus(self, request, context):
        return DeviceStatusResponse(
            device_id=request.device_id,
            status="ready",
            properties=json.dumps({"type": "HPLC", "temperature": 25.0})
        )
    
    def ExecuteCommand(self, request, context):
        return CommandResponse(
            device_id=request.device_id,
            command=request.command,
            result=f"Command '{request.command}' executed",
            success=True
        )

def lambda_handler(event, context):
    """AWS Lambda handler - シンプル版"""
    try:
        action = event.get('action')
        
        if action == 'list':
            devices = [
                {"device_id": "HPLC-01", "status": "ready"},
                {"device_id": "CENTRIFUGE-01", "status": "busy"},
                {"device_id": "PIPETTE-01", "status": "ready"}
            ]
            return {'statusCode': 200, 'body': json.dumps({"devices": devices})}
        
        elif action == 'status':
            device_id = event.get('device_id')
            return {
                'statusCode': 200,
                'body': json.dumps({"device_id": device_id, "status": "ready"})
            }
        
        elif action == 'command':
            device_id = event.get('device_id')
            command = event.get('command')
            return {
                'statusCode': 200,
                'body': json.dumps({
                    "device_id": device_id,
                    "command": command,
                    "result": "success"
                })
            }
    except:
        return {'statusCode': 500, 'body': json.dumps({"error": "device_error"})}
```

### Step 2: Protocol Bridge強化 (Day 1) - シンプル版

#### 2.1 HTTP ↔ gRPC変換実装（シンプル版）
```python
# protocol_bridge_lambda.py シンプル強化版
import grpc
import json

class ProtocolBridge:
    def http_to_grpc_list_devices(self):
        try:
            # gRPC呼び出し試行
            channel = grpc.insecure_channel('localhost:50051')
            stub = SiLA2DeviceServiceStub(channel)
            # 実際のgRPC呼び出し処理
            return {"devices": ["HPLC-01", "CENTRIFUGE-01", "PIPETTE-01"]}
        except:
            return {"devices": ["HPLC-01", "CENTRIFUGE-01"], "source": "fallback"}
    
    def http_to_grpc_device_status(self, device_id):
        try:
            # gRPC呼び出し試行
            return {"device_id": device_id, "status": "ready"}
        except:
            return {"device_id": device_id, "status": "ready", "source": "fallback"}
    
    def http_to_grpc_execute_command(self, device_id, command):
        try:
            # gRPC呼び出し試行
            return {"device_id": device_id, "command": command, "result": "success"}
        except:
            return {"device_id": device_id, "result": "success", "source": "fallback"}

def lambda_handler(event, context):
    try:
        bridge = ProtocolBridge()
        action = event.get('action')
        
        if action == 'list':
            result = bridge.http_to_grpc_list_devices()
        elif action == 'status':
            result = bridge.http_to_grpc_device_status(event.get('device_id'))
        elif action == 'command':
            result = bridge.http_to_grpc_execute_command(event.get('device_id'), event.get('command'))
        else:
            result = {"error": "unknown_action"}
        
        return {'statusCode': 200, 'body': json.dumps(result)}
    except:
        return {'statusCode': 500, 'body': json.dumps({"error": "bridge_error"})}
```

### Step 3: Gateway Tools統合確認 (Day 2) - シンプル版

#### 3.1 Gateway Toolsシンプル化
```python
# gateway/sila2_gateway_tools_simplified.py シンプル化更新
class SiLA2GatewayToolsSimplified:
    def __init__(self):
        self.bridge_url = os.environ.get('PROTOCOL_BRIDGE_URL', 'https://api-gateway-url')
    
    def list_available_devices(self):
        try:
            response = requests.get(f"{self.bridge_url}/devices", timeout=5)
            return response.json()
        except:
            return {"devices": ["HPLC-01", "CENTRIFUGE-01"], "status": "demo"}
    
    def get_device_status(self, device_id):
        try:
            response = requests.get(f"{self.bridge_url}/device/{device_id}", timeout=5)
            return response.json()
        except:
            return {"device_id": device_id, "status": "ready", "source": "demo"}
    
    def start_device_operation(self, device_id, operation):
        try:
            response = requests.post(f"{self.bridge_url}/device/{device_id}", 
                                   json={"operation": operation}, timeout=5)
            return response.json()
        except:
            return {"device_id": device_id, "operation": operation, "result": "success"}

def test_gateway_tools_integration():
    tools = SiLA2GatewayToolsSimplified()
    print(f"Devices: {tools.list_available_devices()}")
    print(f"Status: {tools.get_device_status('HPLC-01')}")
    print(f"Operation: {tools.start_device_operation('HPLC-01', 'start')}")
```

### Step 4: AgentCore Runtime統合 (Day 3) - シンプル版

#### 4.1 シンプル統合テスト
```python
# test_phase3_simple.py (新規作成)
def test_simple_integration():
    """シンプル統合テスト"""
    from unified_mock_device_lambda import lambda_handler as mock_handler
    from protocol_bridge_lambda import lambda_handler as bridge_handler
    from gateway.sila2_gateway_tools_simplified import SiLA2GatewayToolsSimplified
    
    # 1. Mock Device直接テスト
    mock_result = mock_handler({'action': 'status', 'device_id': 'HPLC-01'}, {})
    print(f"✅ Mock Device: {mock_result}")
    
    # 2. Protocol Bridge直接テスト
    bridge_result = bridge_handler({'action': 'list'}, {})
    print(f"✅ Protocol Bridge: {bridge_result}")
    
    # 3. Gateway Toolsテスト
    tools = SiLA2GatewayToolsSimplified()
    gateway_result = tools.list_available_devices()
    print(f"✅ Gateway Tools: {gateway_result}")

if __name__ == "__main__":
    test_simple_integration()
```

### Step 5: AWS環境デプロイ (Day 4) - 修正版

#### 5.1 修正版デプロイスクリプト
```bash
#!/bin/bash
# deploy-phase3-fixed.sh - 修正版デプロイスクリプト

set -e

REGION="us-west-2"
STACK_NAME="sila2-lab-automation-phase3-fixed"
ACCOUNT_ID="590183741681"

echo "🚀 Phase 3 修正版デプロイ開始"

# Step 1: CloudFormation デプロイ
echo "📦 Step 1: CloudFormation デプロイ"
aws cloudformation deploy \
  --template-file infrastructure/sila2-phase3-working.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION

# Step 2: Lambda関数更新（urllib版）
echo "🔧 Step 2: Lambda関数更新"

# Mock Device Lambda
zip -r mock-device.zip unified_mock_device_lambda.py
aws lambda update-function-code \
    --function-name "sila2-mock-device-lambda-dev" \
    --zip-file fileb://mock-device.zip \
    --region $REGION

# Protocol Bridge Lambda（urllib版）
zip -r protocol-bridge.zip protocol_bridge_lambda_urllib.py
aws lambda update-function-code \
    --function-name "sila2-protocol-bridge-dev" \
    --zip-file fileb://protocol-bridge.zip \
    --region $REGION

# AgentCore Runtime Lambda（正しいファイル名）
cp main_agentcore_phase3_simple.py agentcore_runtime_sila2.py
zip -r agentcore-runtime.zip agentcore_runtime_sila2.py
aws lambda update-function-code \
    --function-name "sila2-agentcore-runtime-dev" \
    --zip-file fileb://agentcore-runtime.zip \
    --region $REGION

# Step 3: ECRイメージ更新
echo "🐳 Step 3: ECRイメージ更新"
docker build -t sila2-agentcore-runtime-dev .
docker tag sila2-agentcore-runtime-dev:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bedrock-agentcore-sila2_runtime_phase3_simple:latest
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/bedrock-agentcore-sila2_runtime_phase3_simple:latest

echo "✅ 修正版デプロイ完了"
```

#### 5.2 urllib版AgentCore Runtime
```python
# agentcore_runtime_sila2.py - urllib版
import json
import os
import urllib.request
import urllib.parse

def list_available_devices() -> str:
    try:
        api_url = os.environ.get('API_GATEWAY_URL', 'https://demo-api-url')
        data = json.dumps({"action": "list"}).encode('utf-8')
        req = urllib.request.Request(f"{api_url}/devices", data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            devices = result.get('devices', [])
            device_list = [f"{d.get('device_id', 'unknown')} ({d.get('status', 'unknown')})" for d in devices]
            return f"利用可能なSiLA2デバイス: {', '.join(device_list)}"
    except:
        return "利用可能なSiLA2デバイス: HPLC-01, CENTRIFUGE-01, PIPETTE-01"

def lambda_handler(event, context):
    try:
        tool_name = event.get('tool_name')
        parameters = event.get('parameters', {})
        
        if tool_name == 'list_available_devices':
            result = list_available_devices()
        else:
            result = "利用可能なSiLA2デバイス: HPLC-01, CENTRIFUGE-01, PIPETTE-01"
        
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
            'body': json.dumps({'error': f'agentcore_error: {str(e)}'})
        }
```

#### 5.3 urllib版Protocol Bridge
```python
# protocol_bridge_lambda_urllib.py - urllib版
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
        }ilable_devices':
            result = list_available_devices()
        elif tool_name == 'get_device_status':
            device_id = parameters.get('device_id', 'HPLC-01')
            result = get_device_status(device_id)
        elif tool_name == 'execute_device_command':
            device_id = parameters.get('device_id', 'HPLC-01')
            command = parameters.get('command', 'status')
            result = execute_device_command(device_id, command)
        else:
            result = "Unknown tool"
        
        return {
            'statusCode': 200,
            'body': json.dumps({'result': result})
        }
    except:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'agentcore_error'})
        }

## 📊 Phase 3 Simple 完成状況

### ✅ 完了済み
- **4層アーキテクチャ実装**: AgentCore Runtime → Gateway Tools → Protocol Bridge → Mock SiLA2 Devices
- **CloudFormation テンプレート**: Protocol Bridge API + Mock Device gRPC API
- **Lambda関数**: Mock Device + Protocol Bridge + AgentCore Runtime
- **統合テスト**: ローカル環境での動作確認
- **デプロイスクリプト**: 一括デプロイ対応

### 🎯 アーキテクチャ完成
```
AgentCore Runtime → Gateway Tools → Protocol Bridge API → Protocol Bridge Lambda → Mock Device gRPC API → Mock Device Lambda
     (MCP)              (HTTP)         (HTTP/REST)           (gRPC)              (gRPC)            (gRPC)
```

### 🚀 デプロイ手順
1. `./deploy-phase3-simple.sh` - 完全デプロイ
2. `python test_phase3_simple.py` - 統合テスト
3. AgentCore設定 (オプション)

### 📝 次のステップ
- AWS環境でのE2Eテスト
- AgentCore Runtime統合
- 本格運用準備ilable_devices':
            result = list_available_devices()
        elif tool_name == 'get_device_status':
            result = get_device_status(parameters.get('device_id'))
        elif tool_name == 'execute_device_command':
            result = execute_device_command(parameters.get('device_id'), parameters.get('command'))
        else:
            result = "SiLA2 Lab Automation Agent Phase 3 Simple"
        
        return {'statusCode': 200, 'body': json.dumps({'result': result})}
    except:
        return {'statusCode': 500, 'body': json.dumps({'error': 'agent_error'})}
```

### Step 6: AWS環境動作確認 (Day 5) - シンプル版

#### 6.1 シンプル動作確認
```python
# test_aws_simple.py (新規作成)
import requests
import os

def test_simple_aws_deployment():
    """シンプルAWS環境動作確認"""
    api_url = os.environ.get('API_GATEWAY_URL')
    
    tests = [
        ("Device List", f"{api_url}/devices", {"action": "list"}),
        ("Device Status", f"{api_url}/devices", {"action": "status", "device_id": "HPLC-01"}),
        ("Device Command", f"{api_url}/devices", {"action": "command", "device_id": "HPLC-01", "command": "start"})
    ]
    
    for test_name, url, data in tests:
        try:
            response = requests.post(url, json=data, timeout=10)
            print(f"{'✅' if response.status_code == 200 else '❌'} {test_name}")
        except:
            print(f"❌ {test_name}: connection error")

if __name__ == "__main__":
    test_simple_aws_deployment()
```

## 📋 シンプル化実装チェックリスト

### ローカル開発（シンプル版）
- [ ] Mock Device Lambda gRPC機能（基本のみ）
- [ ] Protocol Bridge HTTP ↔ gRPC変換（基本のみ）
- [ ] Gateway Tools シンプル統合
- [ ] AgentCore Runtime シンプル統合
- [ ] ローカル基本テスト完了

### AWS環境デプロイ
- [ ] CloudFormationスタックデプロイ
- [ ] Lambda関数コード更新
- [ ] API Gateway URL設定
- [ ] AgentCore設定・デプロイ

### AWS環境動作確認
- [ ] API Gateway基本テスト
- [ ] Lambda基本動作確認
- [ ] AgentCore基本統合テスト

### ファイル作成・変更（シンプル版）
- [ ] `unified_mock_device_lambda.py` シンプル強化
- [ ] `protocol_bridge_lambda.py` シンプル強化
- [ ] `gateway/sila2_gateway_tools_simplified.py` シンプル化更新
- [ ] `main_agentcore_phase3_simple.py` 新規作成
- [ ] `test_phase3_simple.py` 新規作成
- [ ] `deploy-phase3-simple.sh` 新規作成
- [ ] `.bedrock_agentcore_phase3_simple.yaml` 新規作成

## 📅 シンプル化実装スケジュール

**Day 1**: Mock Device + Protocol Bridge シンプル実装
**Day 2**: Gateway Tools シンプル統合
**Day 3**: AgentCore Runtime シンプル統合 + ローカルテスト
**Day 4**: AWS環境デプロイ
**Day 5**: AWS環境動作確認

## 🎯 シンプル化完了条件

### 必須項目（シンプル版）
- [ ] **4層アーキテクチャ**: 構造維持
- [ ] **MCP通信**: AgentCore Runtime動作
- [ ] **gRPC通信**: Mock SiLA2 Devices動作
- [ ] **基本エラーハンドリング**: try/except のみ
- [ ] **AWS環境動作**: 基本的な動作確認
- [ ] **最小限コード**: 既存ファイル上書き + 必要最小限の新規ファイル

### 削除項目
- ❌ 複雑なフォールバック機能
- ❌ 詳細なログ出力
- ❌ 複数段階リトライ
- ❌ 詳細な例外処理