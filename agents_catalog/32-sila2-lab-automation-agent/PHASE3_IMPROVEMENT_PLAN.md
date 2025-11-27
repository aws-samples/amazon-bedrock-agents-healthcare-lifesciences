# Phase 3 改善版実装計画書
# SiLA2 Lab Automation Agent - gRPC統合アーキテクチャ

**作成日**: 2025-01-27  
**ステータス**: Task Group 0 完了 - 実装準備完了  
**優先度**: HIGH 🔥  
**Task 0 完了日**: 2025-01-27

---

## 📋 目次

1. [概要](#概要)
2. [現状の問題点](#現状の問題点)
3. [改善後のアーキテクチャ](#改善後のアーキテクチャ)
4. [実装タスク一覧](#実装タスク一覧)
5. [技術仕様](#技術仕様)
6. [Phase 4への移行パス](#phase-4への移行パス)

---

## 概要

### 目的
MCP-gRPC Bridge LambdaとMock Device Lambdaの間にApplication Load Balancer (ALB) を追加し、Phase 4でのエッジSiLA2機器接続への移行を容易にする。

### 主な変更点
1. **API Gateway #1 (`82lhs2drfk`)**: 削除
2. **API Gateway #2 (`ib5h74dpr1`)**: 削除（ALBに置き換え）
3. **Application Load Balancer (ALB)**: 新規作成（HTTP/2 + gRPC対応）
4. **MCP-gRPC Bridge Lambda**: gRPCクライアント実装
5. **Mock Device Lambda**: 既存のgRPCサーバー機能を有効化

### メリット
- ✅ Phase 4でエッジ実機器接続時、ALBターゲットグループ変更のみで対応可能
- ✅ MCP-gRPC Bridgeのコード変更不要
- ✅ 本番とテストで同じアーキテクチャ
- ✅ SiLA2プロトコル準拠のgRPC通信
- ✅ HTTP/2ネイティブサポート
- ✅ VPC統合によるセキュアな実機器接続

---

## 現状の問題点

### 現在のアーキテクチャ

```
AgentCore Gateway
    ↓ Direct Lambda Invoke
MCP-gRPC Bridge Lambda
    ↓ boto3 Lambda Invoke (JSON) ← 問題: API Gateway未使用
Mock Device Lambdas
```

### 問題点

1. **API Gatewayが本番フローで未使用**
   - テスト用API Gateway (`ib5h74dpr1`) は存在するが本番未使用
   - 未使用のAPI Gateway (`82lhs2drfk`) が存在

2. **Phase 4への移行が困難**
   - 実機器接続時、MCP-gRPC Bridgeの大幅な変更が必要
   - Mock/Real切り替えロジックの実装が複雑

3. **gRPC機能が未活用**
   - Mock Device LambdaにgRPCサーバー実装済みだが未使用
   - SiLA2プロトコル準拠のgRPC通信が未実装

---

## 改善後のアーキテクチャ

### Phase 3 改善版 (ALB統合)

```
┌────────────────────────────────────────────────────────────────────────┐
│  AgentCore Runtime                                                     │
│  (main_agentcore_phase3.py)                                           │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                                 │ SigV4 HTTP
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Bedrock Claude 3.5 Sonnet v2                                          │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                                 │ Tool Execution
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│  AgentCore Gateway                                                     │
│  (sila2-gateway-1764231790-6an1qmwnun)                                │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                                 │ Direct Lambda Invoke
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│  MCP-gRPC Bridge Lambda                                                │
│  (mcp-grpc-bridge-dev)                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  NEW: gRPCクライアント実装                                         │ │
│  │  • grpc.secure_channel(ALB_ENDPOINT)                              │ │
│  │  • sila2_basic_pb2_grpc.SiLA2DeviceStub()                         │ │
│  │  • GetDeviceInfo() / ExecuteCommand()                             │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                                 │ gRPC over HTTPS (HTTP/2)
                                 │ SiLA2プロトコル準拠
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Application Load Balancer (ALB)                                       │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  NEW: ALB設定                                                      │ │
│  │  • HTTP/2有効化                                                    │ │
│  │  • gRPC Passthrough                                                │ │
│  │  • ターゲットグループ: Lambda                                       │ │
│  │  • ヘルスチェック: gRPC                                            │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                                 │ gRPC (SiLA2プロトコル)
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ Mock HPLC Lambda    │ │ Mock Centrifuge     │ │ Mock Pipette        │
│                     │ │ Lambda              │ │ Lambda              │
│ ┌─────────────────┐ │ │ ┌─────────────────┐ │ │ ┌─────────────────┐ │
│ │ gRPC Server     │ │ │ │ gRPC Server     │ │ │ │ gRPC Server     │ │
│ │ (有効化)         │ │ │ │ (有効化)         │ │ │ │ (有効化)         │ │
│ │                 │ │ │ │                 │ │ │ │                 │ │
│ │ HPLCDevice      │ │ │ │ Centrifuge      │ │ │ │ Pipette         │ │
│ │ Service         │ │ │ │ Service         │ │ │ │ Service         │ │
│ └─────────────────┘ │ │ └─────────────────┘ │ │ └─────────────────┘ │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

---

## 実装タスク一覧

### Task Group 0: 事前調査・リソース確認 ✅ **完了** (2025-01-27)

#### Task 0.1: 既存リソース棚卸し ✅ **完了**
- **優先度**: CRITICAL 🔥
- **工数**: 0.5h（実績）
- **担当**: DevOps + Developer
- **結果**:
  - API Gateway `82lhs2drfk`: ❌ 存在しない（設定ファイルから削除のみ必要）
  - API Gateway `ib5h74dpr1`: ✅ 存在（REST API、削除は後で実施）
  - Lambda関数: 4個確認（mcp-grpc-bridge-dev, mock-hplc-device-dev, mock-centrifuge-device-dev, mock-pipette-device-dev）
  - Lambda Layer: grpc-layer-v2 (Python 3.10) 使用中
- **成果物**: ✅
  - `docs/RESOURCE_INVENTORY.md`

#### Task 0.2: gRPC実装状況確認 ✅ **完了**
- **優先度**: CRITICAL 🔥
- **工数**: 0.5h（実績）
- **担当**: Developer
- **結果**:
  - gRPCサーバー実装: ✅ 完全実装済み（HPLCDeviceServiceクラス）
  - protobufファイル: ✅ 正常に生成済み
  - Lambda Layer: ✅ grpc-layer-v2 (v6) 存在
  - 状態: 実装済みだが未有効化（環境変数 GRPC_ENABLED=false）
- **成果物**: ✅
  - `docs/GRPC_STATUS_REPORT.md`

#### Task 0.3: ALB採用決定 ✅ **完了**
- **優先度**: CRITICAL 🔥
- **工数**: 0.33h（実績）
- **担当**: DevOps
- **決定**: ✅ **Application Load Balancer (ALB) を採用**
- **理由**:
  - Phase 4への移行容易性（ターゲットグループ変更のみ）
  - gRPCネイティブサポート（HTTP/2 Passthrough）
  - VPC統合によるセキュアな実機器接続
- **コスト**: 月間約$20-30（長期的にコスト効率良）
- **成果物**: ✅
  - `docs/ALB_ADOPTION_DECISION.md`

#### Task 0.4: Phase 3 → Phase 3改善版の影響範囲分析 ✅ **完了**
- **優先度**: HIGH
- **工数**: 0.5h（実績）
- **担当**: Tech Lead
- **結果**:
  - ダウンタイム見積もり: 5分
  - 合計所要時間: 60分
  - リスク評価: 🟡 MEDIUM RISK（管理可能）
  - ロールバック戦略: 4シナリオ準備完了
- **成果物**: ✅
  - `docs/IMPACT_ANALYSIS.md`
  - `docs/TASK_GROUP_0_SUMMARY.md`

---

### Task Group 1: 環境準備・クリーンアップ

#### Task 1.1: 設定ファイル修正
- **優先度**: HIGH
- **工数**: 0.25h
- **担当**: DevOps
- **内容**:
  - `.phase3-config` ファイルから `82lhs2drfk` エントリ削除（**注**: API Gatewayは既に存在しない）
  - `LAMBDA_FUNCTIONS` を実際の関数名に修正
  - API Gateway `ib5h74dpr1` の使用状況確認（削除は後で実施）
- **成果物**:
  - 更新された `.phase3-config`
  - API Gateway使用状況レポート

#### Task 1.2: 開発環境セットアップ
- **優先度**: HIGH
- **工数**: 1h
- **担当**: Developer
- **内容**:
  - Python 3.10環境確認
  - grpcio, protobuf依存関係確認
  - SiLA2プロトコルバッファファイル確認
- **成果物**:
  - 環境確認チェックリスト
  - 依存関係一覧

---

### Task Group 2: Application Load Balancer (ALB) 統合

#### Task 2.1: ALB作成・設定
- **優先度**: HIGH
- **工数**: 2.5h
- **担当**: DevOps
- **内容**:
  - Application Load Balancer作成
  - HTTP/2プロトコル有効化
  - SSL/TLS証明書設定 (ACM)
  - セキュリティグループ設定
  - VPC・サブネット設定
- **ファイル**:
  - `infrastructure/device_alb.yaml` (新規作成)
- **成果物**:
  - CloudFormationテンプレート
  - ALBエンドポイントURL

#### Task 2.2: ターゲットグループ設定
- **優先度**: HIGH
- **工数**: 2h
- **担当**: DevOps
- **内容**:
  - Lambda ターゲットグループ作成 (3つ: HPLC, Centrifuge, Pipette)
  - ヘルスチェック設定 (gRPC対応)
  - ターゲット登録 (Mock Device Lambda)
  - スティッキーセッション設定
- **ファイル**:
  - `infrastructure/device_alb.yaml` (更新)
- **成果物**:
  - ターゲットグループ設定ドキュメント

#### Task 2.3: ALBリスナールール設定
- **優先度**: HIGH
- **工数**: 1.5h
- **担当**: DevOps
- **内容**:
  - HTTPSリスナー作成 (ポート443)
  - gRPCルーティングルール設定
  - パスベースルーティング (/SiLA2Device/*)
  - デフォルトアクション設定
- **ファイル**:
  - `infrastructure/device_alb.yaml` (更新)
- **成果物**:
  - リスナールール設定ドキュメント

#### Task 2.4: Lambda権限設定
- **優先度**: MEDIUM
- **工数**: 0.5h
- **担当**: DevOps
- **内容**:
  - ALBからMock Device Lambda呼び出し権限追加
  - IAMロール更新
  - Lambda関数ポリシー更新
- **成果物**:
  - 権限設定ドキュメント

---

### Task Group 3: MCP-gRPC Bridge Lambda更新

#### Task 3.1: gRPCクライアント実装
- **優先度**: HIGH
- **工数**: 3h
- **担当**: Developer
- **内容**:
  - grpcクライアント実装
  - SiLA2プロトコルスタブ生成
  - GetDeviceInfo() 実装
  - ExecuteCommand() 実装
  - エラーハンドリング
- **ファイル**:
  - `mcp_grpc_bridge_lambda_grpc.py` (新規作成)
- **成果物**:
  - gRPCクライアント実装コード
  - ユニットテスト

#### Task 3.2: デバイスルーティング更新
- **優先度**: MEDIUM
- **工数**: 2h
- **担当**: Developer
- **内容**:
  - boto3 Lambda Invoke → gRPC呼び出しに変更
  - デバイスタイプ別ルーティング維持
  - 環境変数 `DEVICE_API_URL` 追加
- **ファイル**:
  - `mcp_grpc_bridge_lambda_grpc.py` (更新)
- **成果物**:
  - 更新されたルーティングロジック

#### Task 3.3: 環境変数設定
- **優先度**: MEDIUM
- **工数**: 0.5h
- **担当**: DevOps
- **内容**:
  - `ALB_ENDPOINT` 環境変数追加
  - gRPCエンドポイントURL設定 (ALB DNS名)
  - SSL/TLS設定
- **成果物**:
  - Lambda環境変数設定ドキュメントmbda環境変数設定ドキュメント

---

### Task Group 4: Mock Device Lambda更新

#### Task 4.1: gRPCサーバー有効化
- **優先度**: HIGH
- **工数**: 2h
- **担当**: Developer
- **内容**:
  - 既存のgRPCサーバー機能を有効化
  - Lambda handlerとgRPCサーバーの統合
  - 環境変数 `GRPC_ENABLED=true` 設定
- **ファイル**:
  - `mock_hplc_device_lambda.py` (更新)
  - `mock_centrifuge_device_lambda.py` (更新)
  - `mock_pipette_device_lambda.py` (更新)
- **成果物**:
  - 更新されたMock Device Lambda (3ファイル)

#### Task 4.2: SiLA2プロトコル検証
- **優先度**: MEDIUM
- **工数**: 1.5h
- **担当**: Developer
- **内容**:
  - GetDeviceInfo() レスポンス検証
  - ExecuteCommand() レスポンス検証
  - SiLA2準拠確認
- **成果物**:
  - プロトコル検証レポート

---

### Task Group 5: デプロイ・統合

#### Task 5.1: CloudFormationテンプレート作成
- **優先度**: HIGH
- **工数**: 2h
- **担当**: DevOps
- **内容**:
  - API Gateway gRPC統合テンプレート
  - Lambda更新テンプレート
  - 環境変数設定
- **ファイル**:
  - `infrastructure/phase3_improvement.yaml` (新規作成)
- **成果物**:
  - CloudFormationテンプレート

#### Task 5.2: デプロイスクリプト作成
- **優先度**: HIGH
- **工数**: 1.5h
- **担当**: DevOps
- **内容**:
  - 段階的デプロイスクリプト
  - ロールバック手順
  - 検証スクリプト
- **ファイル**:
  - `scripts/deploy_phase3_improvement.sh` (新規作成)
- **成果物**:
  - デプロイスクリプト
  - ロールバック手順書

#### Task 5.3: 既存デプロイスクリプト修正
- **優先度**: HIGH
- **工数**: 2h
- **担当**: DevOps
- **内容**:
  - `scripts/02_deploy_mock_devices.sh` 更新 (gRPCサーバー有効化)
  - `scripts/03_setup_mcp_bridge.sh` 更新 (gRPCクライアント実装)
  - `scripts/04_create_device_gateway.sh` 更新 (gRPC統合設定)
  - `scripts/deploy_all.sh` 更新 (Phase 3改善版対応)
  - `scripts/DEPLOYMENT_ORDER.md` 更新 (gRPCフロー説明追加)
- **ファイル**:
  - `scripts/02_deploy_mock_devices.sh` (更新)
  - `scripts/03_setup_mcp_bridge.sh` (更新)
  - `scripts/04_create_device_gateway.sh` (更新)
  - `scripts/deploy_all.sh` (更新)
  - `scripts/DEPLOYMENT_ORDER.md` (更新)
- **成果物**:
  - 更新されたデプロイスクリプト (5ファイル)
  - デプロイ手順書

#### Task 5.4: 統合デプロイ
- **優先度**: HIGH
- **工数**: 1h
- **担当**: DevOps
- **内容**:
  - API Gateway更新デプロイ
  - Lambda更新デプロイ
  - 環境変数設定
  - 動作確認
- **成果物**:
  - デプロイ完了レポート

---

### Task Group 6: テスト・検証

#### Task 6.1: ユニットテスト作成
- **優先度**: HIGH
- **工数**: 3h
- **担当**: Developer
- **内容**:
  - MCP-gRPC Bridge gRPCクライアントテスト
  - Mock Device gRPCサーバーテスト
  - プロトコル変換テスト
- **ファイル**:
  - `tests/test_grpc_client.py` (新規作成)
  - `tests/test_grpc_server.py` (新規作成)
- **成果物**:
  - ユニットテストコード
  - テストレポート

#### Task 6.2: 統合テスト更新
- **優先度**: HIGH
- **工数**: 2h
- **担当**: Developer
- **内容**:
  - `test_phase3_integration.py` 更新
  - gRPC通信テスト追加
  - エンドツーエンドテスト
- **ファイル**:
  - `test_phase3_integration.py` (更新)
- **成果物**:
  - 更新された統合テスト

#### Task 6.3: パフォーマンステスト
- **優先度**: MEDIUM
- **工数**: 2h
- **担当**: Developer
- **内容**:
  - レイテンシ測定
  - スループット測定
  - 現状との比較
- **成果物**:
  - パフォーマンステストレポート

---

### Task Group 7: ドキュメント作成

#### Task 7.1: アーキテクチャドキュメント更新
- **優先度**: MEDIUM
- **工数**: 1.5h
- **担当**: Tech Lead
- **内容**:
  - `ARCHITECTURE_ROADMAP.md` 更新
  - Phase 3改善版アーキテクチャ図追加
  - データフロー図更新
- **ファイル**:
  - `ARCHITECTURE_ROADMAP.md` (更新)
- **成果物**:
  - 更新されたアーキテクチャドキュメント

#### Task 7.2: デプロイ手順ドキュメント更新
- **優先度**: HIGH
- **工数**: 1.5h
- **担当**: DevOps
- **内容**:
  - `scripts/DEPLOYMENT_ORDER.md` 詳細更新
  - gRPC統合フローの説明追加
  - 環境変数設定ガイド追加
  - Phase 3 → Phase 3改善版の移行手順
  - ロールバック手順の明確化
- **ファイル**:
  - `scripts/DEPLOYMENT_ORDER.md` (更新)
- **成果物**:
  - 更新されたデプロイ手順書

#### Task 7.3: 運用ドキュメント作成
- **優先度**: MEDIUM
- **工数**: 1h
- **担当**: DevOps
- **内容**:
  - トラブルシューティングガイド
  - gRPC通信のデバッグ方法
  - パフォーマンス監視ガイド
- **ファイル**:
  - `docs/PHASE3_IMPROVEMENT_OPERATIONS.md` (新規作成)
- **成果物**:
  - 運用ドキュメント

---

## 技術仕様

### API Gateway gRPC統合

#### オプションA: gRPC-JSON Transcoding
```yaml
Resources:
  DeviceApiGateway:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: sila2-device-grpc-api
      ProtocolType: HTTP
      Description: SiLA2 Device API with gRPC support
      
  GrpcRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref DeviceApiGateway
      RouteKey: POST /SiLA2Device/{method}
      Target: !Join
        - /
        - - integrations
          - !Ref GrpcIntegration
```

#### オプションB: gRPC Passthrough (推奨)
```yaml
Resources:
  DeviceApiGateway:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: sila2-device-grpc-api
      ProtocolType: HTTP
      CorsConfiguration:
        AllowOrigins: ['*']
        AllowMethods: ['POST']
        AllowHeaders: ['content-type', 'grpc-*']
```

### MCP-gRPC Bridge Lambda

```python
# mcp_grpc_bridge_lambda_grpc.py
import grpc
import sila2_basic_pb2
import sila2_basic_pb2_grpc
import os

DEVICE_API_URL = os.getenv('DEVICE_API_URL', 
    'ib5h74dpr1.execute-api.us-west-2.amazonaws.com:443')

def get_device_status(params):
    device_id = params.get('device_id')
    
    # gRPCチャネル作成
    credentials = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel(DEVICE_API_URL, credentials)
    stub = sila2_basic_pb2_grpc.SiLA2DeviceStub(channel)
    
    # gRPCリクエスト
    request = sila2_basic_pb2.DeviceInfoRequest(device_id=device_id)
    response = stub.GetDeviceInfo(request)
    
    # レスポンス変換
    return {
        'device_id': response.device_id,
        'device_type': response.device_type,
        'status': response.status,
        'properties': dict(response.properties),
        'timestamp': response.timestamp,
        'sila2_compliant': True
    }

def execute_device_command(params):
    device_id = params.get('device_id')
    command = params.get('command')
    parameters = params.get('parameters', {})
    
    # gRPCチャネル作成
    credentials = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel(DEVICE_API_URL, credentials)
    stub = sila2_basic_pb2_grpc.SiLA2DeviceStub(channel)
    
    # gRPCリクエスト
    request = sila2_basic_pb2.CommandRequest(
        device_id=device_id,
        operation=command,
        parameters=parameters
    )
    response = stub.ExecuteCommand(request)
    
    # レスポンス変換
    return {
        'device_id': response.device_id,
        'operation': response.operation,
        'success': response.success,
        'status': response.status,
        'result': dict(response.result),
        'timestamp': response.timestamp,
        'sila2_compliant': True
    }
```

### Mock Device Lambda (gRPCサーバー有効化)

```python
# mock_hplc_device_lambda.py (更新箇所のみ)

# 環境変数でgRPC有効化
GRPC_ENABLED = os.getenv('GRPC_ENABLED', 'true').lower() == 'true'

def lambda_handler(event, context):
    if GRPC_ENABLED:
        # gRPCサーバーモード
        return handle_grpc_request(event, context)
    else:
        # 従来のLambdaモード
        return handle_lambda_request(event, context)
```

---

## Phase 4への移行パス

### Phase 3改善版 → Phase 4 (エッジSiLA2機器接続)

```
Phase 3改善版:
  MCP-gRPC Bridge → ALB → Lambda Target (Mock Device)

Phase 4:
  MCP-gRPC Bridge → ALB → ├─ Lambda Target (Mock Device) - Weight: 10%
                         └─ IP Target (VPC内実機器) - Weight: 90%
```

### 変更点

1. **ALBターゲットグループ追加**
   - IPターゲットグループ作成 (VPC内実機器用)
   - ウェイトベースルーティング設定
   - Canaryデプロイ対応

2. **MCP-gRPC Bridge**
   - **コード変更不要** ✅
   - ALBエンドポイントは同じ

3. **実機器接続**
   - VPC内にgRPCサーバー配置 (エッジSiLA2機器)
   - プライベートサブネット経由
   - セキュアな通信 (VPC内部通信)

4. **段階的移行**
   - Step 1: Mock 100% (Phase 3改善版)
   - Step 2: Mock 90% + Real 10% (テスト)
   - Step 3: Mock 50% + Real 50% (検証)
   - Step 4: Mock 10% + Real 90% (本番)
   - Step 5: Real 100% (完全移行)

---

## タスクサマリー

### 工数見積もり

| Task Group | タスク数 | 合計工数 | 優先度 |
|-----------|---------|---------|--------|
| 0. 事前調査 | 4 | 5.5h | CRITICAL |
| 1. 環境準備 | 2 | 1.5h | HIGH |
| 2. ALB統合 | 4 | 6.5h | HIGH |
| 3. MCP-gRPC Bridge | 3 | 6h | HIGH |
| 4. Mock Device | 2 | 3.5h | HIGH |
| 5. デプロイ | 4 | 6.5h | HIGH |
| 6. テスト | 3 | 7h | HIGH |
| 7. ドキュメント | 3 | 4h | HIGH |
| **合計** | **24** | **40h** | - |

### マイルストーン

- **Week 0 (事前準備)**: Task Group 0 完了 (事前調査・技術検証) - **実装開始前に必須** ⚠️
- **Week 1**: Task Group 1-2 完了 (環境準備 + API Gateway)
- **Week 2**: Task Group 3-4 完了 (Lambda更新)
- **Week 3**: Task Group 5-6 完了 (デプロイ + テスト)
- **Week 4**: Task Group 7 完了 (ドキュメント) + 本番デプロイ

---

## リスク管理

### 高リスク

1. **ALB + Lambda gRPC統合の技術的課題** ⚠️
   - リスク: LambdaはHTTP/2をサポートするが、gRPCサーバーとしての制約がある可能性
   - 軽減策: Task 0.3でALB + LambdaのgRPC統合をPoC検証
   - 代替案: LambdaをFargateに移行してgRPCサーバーを実装

2. **ALBコスト増加**
   - リスク: API Gatewayと比較してALBのコストが高い
   - 軽減策: Phase 4での実機器接続を考慮すると、長期的にはコスト効率が良い
   - 代替案: なし（ALBが最適解）

### 中リスク

1. **既存機能への影響**
   - 軽減策: 段階的デプロイ + ロールバック手順準備

2. **テスト不足**
   - 軽減策: 包括的なテスト計画

---

## 承認

### Phase 1: 事前調査承認
- [ ] Task Group 0 実施承認
- [ ] 技術検証予算承認
- [ ] リソース棚卸し承認

### Phase 2: 実装承認（Task Group 0完了後）
- [ ] 技術検証結果レビュー
- [ ] アーキテクチャ最終決定
- [ ] Tech Lead承認
- [ ] DevOps承認
- [ ] Security承認
- [ ] 実装開始承認

---

**次のステップ**: 
1. **必須**: Task Group 0 (事前調査) を完了
2. 技術検証結果に基づきアーキテクチャを最終決定
3. 承認後、Task Group 1から順次実装開始
