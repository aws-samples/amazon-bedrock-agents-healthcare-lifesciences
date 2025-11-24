# SiLA2 Lab Automation Agent - 開発計画

## 🎯 プロジェクト概要

**目標**: AIエージェントでSiLA2を通じて実験機器を制御するデモアプリケーション

**最終アーキテクチャ**: AgentCore → Gateway → SiLA2 → 実験機器

## 📅 開発フェーズ

### Phase 1: MCP統合基盤 ✅ **完了**

#### ✅ 完了条件
- [x] AWS環境でMCP経由SiLA2ツール実行成功 ✅
- [x] 全テストケース PASS ✅
- [x] 性能・安定性確認完了 ✅

---

### Phase 2: AgentCore Gateway統合 ✅ **完了**
**完了日**: 2025-01-XX
**最終確認**: AgentCore Gatewayネイティブ統合完了
**デプロイスクリプト**: `deploy-agentcore-gateway.sh`

#### ✅ **成功した実装**
- **AgentCore Gateway**: ネイティブ統合でSiLA2ツール実行
- **シンプルアーキテクチャ**: API Gateway + Lambdaレイヤーを削除
- **マネージドサービス**: 自動スケーリングとセキュリティ
- **低レイテンシ**: 直接統合でオーバーヘッド最小化

#### ✅ **技術的成果**
- **AgentCore Gateway**: SiLA2-MCPブリッジをGateway内で実装
- **レイヤー削減**: 4層→ 2層にシンプル化
- **AWS戦略合致**: AgentCore推進に沿った最新技術スタック
- **運用効率**: マネージドサービスで運用負荷最小化

#### ✅ **デプロイ手順**
```bash
# 1. 依存関係インストール
source .venv/bin/activate
pip install -r requirements.txt

# 2. AWS認証確認
aws sts get-caller-identity

# 3. AgentCore Gatewayデプロイ
./deploy-agentcore-gateway.sh

# 4. 動作確認
agentcore gateway status --name sila2-lab-automation-gateway
agentcore invoke '{"prompt": "List all available SiLA2 devices"}'
```

#### ✅ **動作確認**
```bash
agentcore invoke '{"prompt": "List all available SiLA2 devices"}'
```
**応答例**:
```
There are three SiLA2 devices currently available in the laboratory:
1. An HPLC system (HPLC-01) which is ready for use
2. A Centrifuge (CENTRIFUGE-01) which is currently busy  
3. A Pipette (PIPETTE-01) which is ready for use
```

#### ✅ **AgentCore Gateway動作確認**
- **ネイティブ統合**: Gateway内でSiLA2ツール直接実行
- **自動スケーリング**: トラフィックに応じた自動調整
- **統合セキュリティ**: IAM、VPC、暗号化が標準装備
- **低レイテンシ**: 直接通信でオーバーヘッド最小

#### ✅ 完了条件
- [x] AgentCore Gateway経由SiLA2ツール実行成功 ✅
- [x] **レイヤーシンプル化完了** ✅
- [x] **マネージドサービス統合** ✅
- [x] **AWS戦略合致確認** ✅

---

### Phase 3: SiLA2 Protocol実装 🚧 **次のフェーズ** - **デモ向け最小実装**
**開始条件**: Phase 2完了 ✅
**目標**: デモに必要な最小限のSiLA2機能実装
**予想期間**: 1-2週間 (簡素化)

#### 🎯 具体的な実装計画

##### 3.1 SiLA2プロトコル基盤 (Week 1) - **デモ向け最小構成**
- **最小限ライブラリ統合**
  ```python
  # requirements-phase3-minimal.txt
  sila2lib>=0.10.0          # 基本機能のみ
  grpcio>=1.50.0            # gRPC core
  protobuf>=4.21.0          # Protocol Buffers
  ```
- **基本SiLA2クライアント**
  - デバイス発見: 固定エンドポイント使用 (mDNS省略)
  - 接続管理: シンプルな同期接続のみ
  - 最小限のエラーハンドリング

##### 3.2 デモ用デバイス定義 (Week 1) - **最小機能セット**
- **デモ用Features (3つのみ)**
  - `StatusProvider`: デバイス状態取得のみ
  - `SimulationController`: 基本的な開始/停止
  - カスタム機能は省略
- **固定デバイス設定**
  ```json
  {
    "devices": [
      {"id": "HPLC-01", "type": "HPLC", "port": 50051},
      {"id": "CENTRIFUGE-01", "type": "Centrifuge", "port": 50052},
      {"id": "PIPETTE-01", "type": "Pipette", "port": 50053}
    ]
  }
  ```

##### 3.3 統一Mock Device Lambda (Week 1) - **統一Lambdaアーキテクチャ**
- **統一Lambda構成**
  ```python
  # 統一Mock Device Lambda実装
  class UnifiedMockDeviceLambda:
      def __init__(self):
          self.device_simulators = {
              'hplc': HPLCSimulator(),
              'centrifuge': CentrifugeSimulator(),
              'pipette': PipetteSimulator()
          }
      
      def lambda_handler(self, event, context):
          device_type = event['pathParameters']['device_type']
          device_id = event['pathParameters']['device_id']
          action = event['pathParameters']['action']
          
          simulator = self.device_simulators[device_type]
          return simulator.handle_request(action, device_id, event)
  ```
- **デバイスシミュレーター**
  ```python
  class DeviceSimulator:
      def handle_request(self, action: str, device_id: str, event: dict):
          method = getattr(self, f"handle_{action}", None)
          if not method:
              raise ValueError(f"Unsupported action: {action}")
          return method(device_id, event)
  
  class HPLCSimulator(DeviceSimulator):
      def handle_get_status(self, device_id: str, event: dict):
          return {'device_id': device_id, 'status': 'ready', 'temperature': 25.0}
  ```
- **基本テスト**
  - API Gateway + 統一Lambda接続テスト
  - デバイスファクトリーパターンテスト
  - 複数デバイスタイプ対応テスト

##### 3.4 Gateway統合 (Week 2) - **統一Lambda統合**
- **統一Lambdaブリッジ**
  ```python
  class UnifiedLambdaBridge:
      def __init__(self):
          self.api_endpoint = "https://api-gateway-url/mock-devices"
          self.device_types = ["hplc", "centrifuge", "pipette"]
      
      def list_devices(self): 
          devices = []
          for device_type in self.device_types:
              response = requests.get(f"{self.api_endpoint}/{device_type}/list")
              devices.extend(response.json())
          return devices
      
      def get_device_status(self, device_type: str, device_id: str): 
          return requests.get(f"{self.api_endpoint}/{device_type}/{device_id}/get_status").json()
      
      def execute_device_command(self, device_type: str, device_id: str, command: str): 
          return requests.post(f"{self.api_endpoint}/{device_type}/{device_id}/execute_command", 
                             json={"command": command}).json()
  ```
- **エラーハンドリング強化**
  - HTTPステータスコードチェック
  - Lambdaタイムアウト対応
  - デバイスタイプバリデーション

##### 3.5 統合テスト (Week 3)
- **End-to-Endテスト**
  - AgentCore → Gateway → SiLA2 → Virtual Device
  - 複数デバイス同時制御
  - 長時間実行テスト
- **パフォーマンステスト**
  - レスポンス時間測定
  - スループット測定
  - リソース使用量監視

#### 🔧 技術スタック追加 - **統一Lambda構成**
- **SiLA2ライブラリ**: `sila2lib>=0.10.0` (基本機能のみ)
- **プロトコル**: `grpcio>=1.50.0` + `protobuf>=4.21.0`
- **Mock Devices**: 統一Lambda (コスト効率重視)
- **HTTP Client**: `requests>=2.28.0`
- **テスト**: 基本的な`pytest` + Lambdaテスト

#### 📋 成果物 - **統一Lambda実装**
- 基本的なSiLA2クライアント統合
- 統一Mock Device Lambda (3種類のデバイスシミュレーター)
- AgentCore Gateway統合コード
- デバイスファクトリーパターン実装
- 統一Lambdaテストスイート
- デモシナリオドキュメント

#### ✅ デモアプリのメリット
- ✅ **開発時間短縮**: 最小限の機能実装
- ✅ **デモ効果**: 主要機能の動作確認
- ✅ **保守性**: シンプルなコード構成
- ✅ **拡張性**: 必要に応じて機能追加可能
- ✅ **理解しやすさ**: 概念実証に最適

#### ✅ 完了条件
- [ ] SiLA2プロトコル通信確立
- [ ] 仮想デバイス3台との通信成功
- [ ] AgentCore経由でのSiLA2コマンド実行
- [ ] エラーハンドリング動作確認
- [ ] パフォーマンス要件達成 (<2秒応答時間)
- [ ] 統合テスト全項目PASS

### Phase 4: Tecan Fluent統合 ⏳
**開始条件**: Phase 3完了後
**目標**: 実際の液体ハンドリングロボット統合
**予想期間**: 3-4週間

#### 計画中の実装
- Tecan Fluent SiLA2コネクタ実装
- 実機テスト環境構築
- 液体ハンドリングワークフロー
- 安全性・信頼性強化

### Phase 5: 統合・最適化 ⏳
**開始条件**: Phase 4完了後
**目標**: 本番環境対応と性能最適化
**予想期間**: 2-3週間

#### 計画中の実装
- 本番環境デプロイ
- 監視・ログ強化
- セキュリティ強化
- ドキュメント整備

## 🔧 技術スタック

### Phase 2で確立された技術構成
- **AgentCore Runtime**: BedrockAgentCoreApp
- **AI Framework**: Strands Agents SDK
- **Gateway**: AgentCore Gateway (ネイティブ)
- **LLM**: Anthropic Claude 3.5 Sonnet v2
- **デプロイ**: AgentCore CLI
- **監視**: CloudWatch + X-Ray
- **インフラ**: AgentCoreマネージドサービス
- **コンテナ**: Amazon ECR

### アーキテクチャ概要
```
User → AgentCore Runtime → AgentCore Gateway → SiLA2 Tools → Lab Devices
```

### 成功要因
1. **アーキテクチャシンプル化**: レイヤー数を4→ 2に削減
2. **AWS最新技術採用**: AgentCore Gatewayのネイティブ統合
3. **マネージドサービス活用**: 運用負荷の最小化
4. **直接統合**: オーバーヘッドとレイテンシの最小化
5. **AWS戦略合致**: AgentCore推進に沿った技術選定

## 🎯 次のステップ

### Phase 3準備
- SiLA2プロトコル仕様調査
- 実験機器API設計
- テストデバイス選定
- 開発環境準備

### 継続的改善
- エラーハンドリング強化
- ログ出力改善
- パフォーマンス最適化
- セキュリティ強化

## 📦 デプロイメント

### 前提条件
- AWS CLI設定済み
- Python 3.9+
- Docker (AgentCore Runtime用)
- 必要なAWSサービスへのアクセス権限

### クイックスタート
```bash
# リポジトリクローン
git clone <repository-url>
cd agents_catalog/32-sila2-lab-automation-agent

# 仮想環境セットアップ
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# デプロイ実行
./deploy-corrected.sh

# 動作確認
agentcore status
agentcore invoke '{"prompt": "List all lab devices"}'
```

### デプロイ内容
- **AgentCore Gateway**: ネイティブSiLA2ツール統合
- **ECR**: AgentCore Runtime コンテナイメージ
- **マネージドサービス**: 自動スケーリング、セキュリティ、監視
- **SiLA2 Bridge**: Gateway内で直接実装