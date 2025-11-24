# Phase 3 完全実装計画

## 🎯 現状分析

### 現在の実装状況 (Phase 2.5)
```
AgentCore Runtime → 直接SiLA2ツール実行 (固定レスポンス)
```

### Phase 3 目標アーキテクチャ
```
AgentCore Runtime → Gateway → API Gateway + Lambda → Mock SiLA2 Devices (gRPC)
```

## 🚧 実装ギャップ

### 未実装コンポーネント
1. **Protocol Bridge Layer**: API Gateway + Lambda
2. **gRPC Mock Devices**: Lambda-based SiLA2 Devices
3. **Gateway Tools簡素化**: HTTP-based通信

## 📅 完全実装計画

### Step 1: インフラストラクチャ構築 (Day 1-2)

#### 1.1 API Gateway + Lambda デプロイ
```bash
# infrastructure/sila2-phase3-working.yaml をデプロイ
aws cloudformation deploy \
  --template-file infrastructure/sila2-phase3-working.yaml \
  --stack-name sila2-phase3-infrastructure \
  --capabilities CAPABILITY_IAM
```

#### 1.2 必要なファイル
- `infrastructure/sila2-phase3-working.yaml` ✅ (既存)
- `unified_mock_device_lambda.py` ✅ (既存)
- `protocol_bridge_lambda.py` ✅ (既存)

### Step 2: Protocol Bridge実装 (Day 2-3)

#### 2.1 HTTP ↔ gRPC変換Lambda
```python
# protocol_bridge_lambda.py (既存ファイル強化)
def lambda_handler(event, context):
    """HTTP リクエストをgRPCに変換"""
    action = event.get('action')
    device_id = event.get('device_id')
    
    # gRPC クライアント作成
    grpc_client = create_grpc_client(device_id)
    
    if action == 'list':
        return list_devices_grpc()
    elif action == 'status':
        return get_device_status_grpc(grpc_client, device_id)
    elif action == 'command':
        command = event.get('command')
        return execute_command_grpc(grpc_client, device_id, command)
```

#### 2.2 デバイスレジストリ
```python
# device_registry.py (新規作成)
DEVICE_REGISTRY = {
    'HPLC-01': {'type': 'hplc', 'grpc_endpoint': 'lambda://hplc-simulator'},
    'CENTRIFUGE-01': {'type': 'centrifuge', 'grpc_endpoint': 'lambda://centrifuge-simulator'},
    'PIPETTE-01': {'type': 'pipette', 'grpc_endpoint': 'lambda://pipette-simulator'}
}
```

### Step 3: Mock SiLA2 Devices (gRPC) 実装 (Day 3-4)

#### 3.1 gRPC Server in Lambda
```python
# unified_mock_device_lambda.py (既存ファイル強化)
import grpc
from concurrent import futures
import sila2_basic_pb2_grpc

class SiLA2DeviceServicer(sila2_basic_pb2_grpc.SiLA2DeviceServicer):
    def __init__(self, device_type):
        self.device_type = device_type
        self.simulators = {
            'hplc': HPLCSimulator(),
            'centrifuge': CentrifugeSimulator(),
            'pipette': PipetteSimulator()
        }
    
    def GetStatus(self, request, context):
        simulator = self.simulators[self.device_type]
        return simulator.get_status(request.device_id)
    
    def ExecuteCommand(self, request, context):
        simulator = self.simulators[self.device_type]
        return simulator.execute_command(request.device_id, request.command)

def lambda_handler(event, context):
    """Lambda内でgRPCサーバー起動"""
    device_type = event.get('device_type', 'hplc')
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sila2_basic_pb2_grpc.add_SiLA2DeviceServicer_to_server(
        SiLA2DeviceServicer(device_type), server)
    
    # Lambda内でgRPC処理
    return handle_grpc_request(event, server)
```

#### 3.2 デバイスシミュレーター強化
```python
class HPLCSimulator:
    def __init__(self):
        self.status = 'ready'
        self.temperature = 25.0
        self.pressure = 100.0
    
    def get_status(self, device_id):
        return {
            'device_id': device_id,
            'status': self.status,
            'temperature': self.temperature,
            'pressure': self.pressure,
            'timestamp': datetime.now().isoformat()
        }
    
    def execute_command(self, device_id, command):
        if command == 'start':
            self.status = 'running'
            return {'result': 'HPLC analysis started'}
        elif command == 'stop':
            self.status = 'ready'
            return {'result': 'HPLC analysis stopped'}
        else:
            return {'result': f'Unknown command: {command}'}
```

### Step 4: Gateway Tools簡素化 (Day 4-5)

#### 4.1 HTTP-based Gateway Tools
```python
# gateway/sila2_gateway_tools_simplified.py (既存ファイル使用)
class SiLA2GatewayTools:
    def __init__(self):
        self.protocol_bridge_url = os.environ.get('PROTOCOL_BRIDGE_URL')
    
    def list_available_devices(self):
        response = requests.post(f"{self.protocol_bridge_url}/devices", 
                               json={"action": "list"})
        return response.json()
    
    def get_device_status(self, device_id: str):
        response = requests.post(f"{self.protocol_bridge_url}/devices",
                               json={"action": "status", "device_id": device_id})
        return response.json()
    
    def execute_device_command(self, device_id: str, command: str):
        response = requests.post(f"{self.protocol_bridge_url}/devices",
                               json={"action": "command", "device_id": device_id, "command": command})
        return response.json()
```

#### 4.2 AgentCore Runtime更新
```python
# main_agentcore_phase3_complete.py (新規作成)
from gateway.sila2_gateway_tools_simplified import SiLA2GatewayTools

app = BedrockAgentCoreApp()
sila2_tools = SiLA2GatewayTools()

@app.entrypoint
def process_request(request_data) -> str:
    prompt = extract_prompt(request_data)
    
    if 'list' in prompt.lower():
        return sila2_tools.list_available_devices()
    elif 'status' in prompt.lower():
        device_id = extract_device_id(prompt)
        return sila2_tools.get_device_status(device_id)
    elif 'command' in prompt.lower():
        device_id, command = extract_device_command(prompt)
        return sila2_tools.execute_device_command(device_id, command)
```

### Step 5: 統合テスト (Day 5-6)

#### 5.1 E2Eテストスイート
```python
# test_phase3_complete.py (新規作成)
def test_full_architecture():
    """AgentCore → Gateway → Protocol Bridge → Mock Devices"""
    
    # 1. デバイス一覧取得テスト
    result = agentcore_invoke("List all devices")
    assert "HPLC-01" in result
    assert "CENTRIFUGE-01" in result
    assert "PIPETTE-01" in result
    
    # 2. デバイス状態取得テスト
    result = agentcore_invoke("Get status of HPLC-01")
    assert "ready" in result
    assert "temperature" in result
    
    # 3. コマンド実行テスト
    result = agentcore_invoke("Start HPLC-01")
    assert "started" in result

def test_grpc_mock_devices():
    """Mock SiLA2 Devices gRPC通信テスト"""
    
    # gRPCクライアント作成
    client = create_grpc_client('HPLC-01')
    
    # ステータス取得
    status = client.GetStatus(device_id='HPLC-01')
    assert status.status == 'ready'
    
    # コマンド実行
    result = client.ExecuteCommand(device_id='HPLC-01', command='start')
    assert 'started' in result.message

def test_protocol_bridge():
    """Protocol Bridge HTTP ↔ gRPC変換テスト"""
    
    # HTTP リクエスト
    response = requests.post(f"{PROTOCOL_BRIDGE_URL}/devices",
                           json={"action": "status", "device_id": "HPLC-01"})
    
    assert response.status_code == 200
    data = response.json()
    assert data['device_id'] == 'HPLC-01'
    assert 'status' in data
```

### Step 6: デプロイ自動化 (Day 6-7)

#### 6.1 統一デプロイスクリプト
```bash
#!/bin/bash
# deploy-phase3-complete.sh (新規作成)

set -e
echo "🚀 Phase 3 完全実装デプロイ開始"

# Step 1: インフラストラクチャ
echo "📦 インフラストラクチャデプロイ中..."
aws cloudformation deploy \
  --template-file infrastructure/sila2-phase3-working.yaml \
  --stack-name sila2-phase3-infrastructure \
  --capabilities CAPABILITY_IAM

# Step 2: Lambda関数更新
echo "⚡ Lambda関数更新中..."
./update-lambda-functions.sh

# Step 3: AgentCore Runtime デプロイ
echo "🤖 AgentCore Runtime デプロイ中..."
agentcore deploy --config .bedrock_agentcore_phase3_complete.yaml

# Step 4: 動作確認
echo "✅ 動作確認中..."
python test_phase3_complete.py

echo "🎉 Phase 3 完全実装デプロイ完了"
```

#### 6.2 設定ファイル
```yaml
# .bedrock_agentcore_phase3_complete.yaml (新規作成)
runtime:
  name: sila2_runtime_phase3_complete
  description: "SiLA2 Lab Automation Agent - Phase 3 Complete"
  
environment:
  PROTOCOL_BRIDGE_URL: "${PROTOCOL_BRIDGE_URL}"
  GRPC_MOCK_DEVICES_URL: "${GRPC_MOCK_DEVICES_URL}"
  
gateway:
  tools_module: "gateway.sila2_gateway_tools_simplified"
  
deployment:
  region: us-west-2
  ecr_repository: sila2-agentcore-phase3-complete
```

## 📋 実装チェックリスト

### インフラストラクチャ
- [ ] API Gateway + Lambda デプロイ
- [ ] IAM ロール・ポリシー設定
- [ ] CloudWatch ログ設定

### Protocol Bridge
- [ ] HTTP ↔ gRPC変換機能
- [ ] デバイスレジストリ実装
- [ ] エラーハンドリング

### Mock SiLA2 Devices
- [ ] gRPC Server in Lambda
- [ ] HPLC Simulator
- [ ] Centrifuge Simulator  
- [ ] Pipette Simulator

### Gateway Tools
- [ ] HTTP-based通信実装
- [ ] AgentCore Runtime統合
- [ ] エラーハンドリング

### テスト
- [ ] 単体テスト (各コンポーネント)
- [ ] 統合テスト (E2E)
- [ ] パフォーマンステスト

### デプロイ
- [ ] 統一デプロイスクリプト
- [ ] 設定ファイル整備
- [ ] 動作確認自動化

## 🎯 完了条件

### 必須項目
- [ ] **4層アーキテクチャ**: Runtime → Gateway → Protocol Bridge → Mock Devices
- [ ] **gRPC通信**: Mock DevicesでSiLA2プロトコル実装
- [ ] **HTTP ↔ gRPC変換**: Protocol Bridgeで正常動作
- [ ] **E2Eテスト**: 全体通信フロー確認
- [ ] **パフォーマンス**: <2秒応答時間達成

### 推奨項目
- [ ] **監視**: CloudWatch + X-Ray設定
- [ ] **ログ**: 各層でのログ出力
- [ ] **エラーハンドリング**: 障害時の適切な応答

## 📅 実装スケジュール

**Week 1**: インフラ + Protocol Bridge + Mock Devices
**Week 2**: Gateway Tools + 統合テスト + デプロイ自動化

## 🔄 Phase 4への移行準備

### 技術的負債解消
- Mock DevicesをReal SiLA2 Devicesに置換
- gRPC通信の最適化
- セキュリティ強化

### 拡張ポイント
- 新デバイスタイプ追加
- ワークフロー機能
- リアルタイム監視