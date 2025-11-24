# Lambda設計戦略 - SiLA2 Protocol Bridge

## 🎯 設計方針

### 課題解決
- **AgentCore GatewayのgRPC制限**: HTTP/RESTのみ対応
- **責任の分離**: プロトコル変換を専用レイヤーに分離
- **スケーラビリティ**: デバイス数増加への対応

### アーキテクチャ原則
1. **単一責任**: 各コンポーネントは明確な役割を持つ
2. **疎結合**: レイヤー間の依存を最小化
3. **拡張性**: 新しいデバイスタイプの追加が容易

---

## 🏗️ Lambda設計オプション

### Option A: 統一Lambda（推奨）

```python
# 統一されたSiLA2プロトコルブリッジ
class SiLA2ProtocolBridge:
    def __init__(self):
        self.device_registry = DeviceRegistry()
        self.protocol_handlers = {
            'tecan_fluent': TecanFluentHandler(),
            'hplc': HPLCHandler(),
            'centrifuge': CentrifugeHandler(),
            'pipette': PipetteHandler()
        }
        self.grpc_clients = {}
    
    def lambda_handler(self, event, context):
        try:
            # HTTPリクエストをパース
            request = self.parse_http_request(event)
            
            # デバイスタイプを特定
            device_id = request['device_id']
            device_type = self.device_registry.get_type(device_id)
            
            # 適切なハンドラーにルーティング
            handler = self.protocol_handlers[device_type]
            result = handler.execute(request)
            
            return self.format_http_response(result)
            
        except Exception as e:
            return self.error_response(str(e))
```

**メリット**:
- 統一されたデバイス管理
- 共通のエラーハンドリング
- コスト効率（単一Lambda）
- 横断的な機能の実装が容易

**デメリット**:
- 単一障害点
- デバイス固有の最適化が困難

### Option B: デバイス別Lambda

```python
# Tecan Fluent専用Lambda
class TecanFluentLambda:
    def __init__(self):
        self.grpc_client = TecanFluentGrpcClient()
    
    def lambda_handler(self, event, context):
        # Tecan Fluent専用ロジック
        return self.handle_tecan_request(event)

# HPLC専用Lambda  
class HPLCLambda:
    def __init__(self):
        self.grpc_client = HPLCGrpcClient()
    
    def lambda_handler(self, event, context):
        # HPLC専用ロジック
        return self.handle_hplc_request(event)
```

**メリット**:
- デバイス固有の最適化
- 独立したデプロイ・スケーリング
- 障害の分離

**デメリット**:
- 管理コストの増加
- 共通機能の重複実装

---

## 🔧 推奨実装戦略

### Phase 3: 統一Lambda + ハンドラーパターン

```python
class DeviceRegistry:
    """デバイス情報の管理"""
    def __init__(self):
        self.devices = {
            'tecan-001': {
                'type': 'tecan_fluent',
                'endpoint': 'tecan-001.lab.local:50051',
                'status': 'active'
            },
            'hplc-001': {
                'type': 'hplc',
                'endpoint': 'hplc-001.lab.local:50052',
                'status': 'active'
            }
        }
    
    def get_device_info(self, device_id: str) -> dict:
        return self.devices.get(device_id)

class SiLA2Handler:
    """SiLA2プロトコル変換の基底クラス"""
    def execute(self, request: dict) -> dict:
        raise NotImplementedError

class TecanFluentHandler(SiLA2Handler):
    """Tecan Fluent専用ハンドラー"""
    def execute(self, request: dict) -> dict:
        # gRPCクライアントでTecan Fluentと通信
        grpc_request = self.convert_to_grpc(request)
        response = self.grpc_client.call(grpc_request)
        return self.convert_from_grpc(response)

class UnifiedSiLA2Bridge:
    """統一されたSiLA2ブリッジ"""
    def __init__(self):
        self.registry = DeviceRegistry()
        self.handlers = {
            'tecan_fluent': TecanFluentHandler(),
            'hplc': HPLCHandler(),
            'centrifuge': CentrifugeHandler()
        }
    
    def route_request(self, device_id: str, command: dict) -> dict:
        device_info = self.registry.get_device_info(device_id)
        if not device_info:
            raise ValueError(f"Device {device_id} not found")
        
        handler = self.handlers[device_info['type']]
        return handler.execute({
            'device_info': device_info,
            'command': command
        })
```

### Phase 4: 必要に応じて分割

トラフィック量とパフォーマンス要件に基づいて判断:

```python
# API Gatewayルーティング設定
{
    "/devices/tecan/*": "tecan-fluent-lambda",
    "/devices/hplc/*": "hplc-lambda", 
    "/devices/centrifuge/*": "centrifuge-lambda",
    "/devices/*": "unified-sila2-lambda"  # fallback
}
```

---

## 📊 パフォーマンス考慮事項

### Lambda設定
```yaml
UnifiedSiLA2Lambda:
  Runtime: python3.11
  MemorySize: 1024  # gRPCクライアント用
  Timeout: 30       # 機器応答時間考慮
  ReservedConcurrency: 10  # 同時実行制限
  Environment:
    DEVICE_REGISTRY_TABLE: !Ref DeviceRegistryTable
    LOG_LEVEL: INFO
```

### gRPC接続管理
```python
class GrpcConnectionPool:
    """gRPC接続の効率的な管理"""
    def __init__(self):
        self.connections = {}
        self.max_connections = 10
    
    def get_connection(self, endpoint: str):
        if endpoint not in self.connections:
            self.connections[endpoint] = grpc.insecure_channel(endpoint)
        return self.connections[endpoint]
    
    def cleanup_idle_connections(self):
        # アイドル接続のクリーンアップ
        pass
```

---

## 🔍 監視・ログ戦略

### CloudWatch Metrics
- Lambda実行時間・エラー率
- デバイス別リクエスト数
- gRPC接続エラー

### 構造化ログ
```python
import json
import logging

logger = logging.getLogger()

def log_device_operation(device_id: str, operation: str, result: str):
    logger.info(json.dumps({
        'timestamp': datetime.utcnow().isoformat(),
        'device_id': device_id,
        'operation': operation,
        'result': result,
        'component': 'sila2-bridge'
    }))
```

---

## 🚀 実装優先度

### 高優先度
1. **統一Lambda基盤** - 基本的なHTTP ↔ gRPC変換
2. **デバイスレジストリ** - DynamoDBベースの管理
3. **エラーハンドリング** - 統一されたエラー処理

### 中優先度
4. **接続プール** - gRPC接続の効率化
5. **監視・ログ** - 運用可視性の向上

### 低優先度
6. **Mock Device Lambda** - 統一デバイスシミュレーター
7. **デバイス別最適化** - 特定デバイス向けの調整
8. **Lambda分割** - 必要に応じた分離

---

## 🎭 Mock Device Lambda設計

### 統一Mock Device Lambda

```python
class UnifiedMockDeviceLambda:
    def __init__(self):
        self.device_simulators = {
            'hplc': HPLCSimulator(),
            'centrifuge': CentrifugeSimulator(),
            'pipette': PipetteSimulator(),
            'tecan_fluent': TecanFluentSimulator()
        }
    
    def lambda_handler(self, event, context):
        try:
            # パスパラメータから情報を抽出
            device_type = event['pathParameters']['device_type']
            device_id = event['pathParameters']['device_id']
            action = event['pathParameters']['action']
            
            # 適切なシミュレーターを選択
            simulator = self.device_simulators[device_type]
            result = simulator.handle_request(action, device_id, event)
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        except Exception as e:
            return self.error_response(str(e))
```

### API Gateway設定
```yaml
# Mock Device用エンドポイント
/mock-devices/{device_type}/{device_id}/{action}
# 例: /mock-devices/hplc/hplc-001/start_analysis
```

### デバイスシミュレーター実装
```python
class DeviceSimulator:
    def handle_request(self, action: str, device_id: str, event: dict) -> dict:
        method = getattr(self, f"handle_{action}", None)
        if not method:
            raise ValueError(f"Unsupported action: {action}")
        return method(device_id, event)

class HPLCSimulator(DeviceSimulator):
    def handle_start_analysis(self, device_id: str, event: dict) -> dict:
        return {
            'device_id': device_id,
            'analysis_id': f'hplc-{uuid.uuid4()}',
            'status': 'started',
            'estimated_duration': 1800
        }
    
    def handle_get_status(self, device_id: str, event: dict) -> dict:
        return {
            'device_id': device_id,
            'status': 'ready',
            'temperature': 25.0,
            'pressure': 150.0
        }
```

### Lambda設定
```yaml
MockDeviceLambda:
  Runtime: python3.11
  MemorySize: 512
  Timeout: 30
  Environment:
    DEVICE_REGISTRY_TABLE: !Ref MockDeviceRegistryTable
    LOG_LEVEL: INFO
```

### Phase 4でのハイブリッド対応
```python
# 複雑なシミュレーションはECS/Fargateに委譲
class EnhancedMockDeviceLambda:
    def route_to_appropriate_service(self, device_type: str, action: str):
        if self.is_complex_simulation(action):
            return self.delegate_to_ecs(device_type, action)
        else:
            return self.handle_locally(device_type, action)
```

この設計により、AgentCore Gatewayをシンプルに保ちつつ、SiLA2の複雑性を適切に分離し、将来の拡張に対応できます。