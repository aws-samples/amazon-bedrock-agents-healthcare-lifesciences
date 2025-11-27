# リソース棚卸しレポート
**作成日**: 2025-01-27  
**タスク**: Task 0.1 - 既存リソース棚卸し  
**ステータス**: ✅ 完了

---

## 📊 調査結果サマリー

### API Gateway

| ID | 名前 | タイプ | ステータス | 削除可否 | 備考 |
|---|---|---|---|---|---|
| `82lhs2drfk` | - | - | ❌ **存在しない** | N/A | .phase3-configに記載あるが実際には存在しない |
| `ib5h74dpr1` | sila2-device-api | REST API (EDGE) | ✅ 存在 | ⚠️ 要確認 | Phase 3で作成、現在テスト用 |

**判定**: 
- `82lhs2drfk`: 既に削除済みまたは誤記載 → `.phase3-config`から削除のみ必要
- `ib5h74dpr1`: ALB移行後に削除予定

---

## 🔧 Lambda関数

### 1. MCP-gRPC Bridge Lambda
- **名前**: `mcp-grpc-bridge-dev`
- **Runtime**: Python 3.10
- **Handler**: `lambda_function.lambda_handler`
- **Role**: `arn:aws:iam::590183741681:role/sila2-phase3-architecture-compl-DeviceApiLambdaRole-CyYxEA1svxeL`
- **環境変数**:
  ```json
  {
    "DEVICE_MODE": "mock",
    "MCP_ENABLED": "true",
    "GRPC_SUPPORT": "true"
  }
  ```
- **状態**: ✅ 稼働中
- **備考**: gRPCクライアント実装が必要（Task 3.1）

### 2. Mock Device Lambda (HPLC)
- **名前**: `mock-hplc-device-dev`
- **Runtime**: Python 3.10
- **Handler**: `mock_hplc_lambda.lambda_handler`
- **Role**: 同上
- **状態**: ✅ 稼働中
- **gRPC実装**: ✅ 実装済み（`HPLCDeviceService`クラス）
- **備考**: gRPCサーバー機能は実装済みだが未有効化

### 3. Mock Device Lambda (Centrifuge)
- **名前**: `mock-centrifuge-device-dev`
- **Runtime**: Python 3.10
- **Handler**: `mock_centrifuge_lambda.lambda_handler`
- **Role**: 同上
- **状態**: ✅ 稼働中

### 4. Mock Device Lambda (Pipette)
- **名前**: `mock-pipette-device-dev`
- **Runtime**: Python 3.10
- **Handler**: `mock_pipette_lambda.lambda_handler`
- **Role**: 同上
- **状態**: ✅ 稼働中

---

## 📦 Lambda Layers

| Layer名 | バージョン | Runtime | 作成日 | 状態 |
|---|---|---|---|---|
| `grpc-layer` | 1 | python3.9 | 2025-11-26 | ⚠️ 旧バージョン |
| `grpc-layer-v2` | 6 | python3.10 | 2025-11-27 | ✅ 最新 |

**判定**: `grpc-layer-v2` (Python 3.10対応) を使用

---

## ☁️ CloudFormation スタック

| スタック名 | ステータス | 作成日 | 備考 |
|---|---|---|---|
| `sila2-phase3-architecture-complete` | CREATE_COMPLETE | 2025-11-27 | 現在の本番スタック |

**依存関係**: 
- Lambda関数 (4個)
- IAM Role (1個)
- API Gateway (1個: ib5h74dpr1)

---

## 🔐 IAM Role

**Role ARN**: `arn:aws:iam::590183741681:role/sila2-phase3-architecture-compl-DeviceApiLambdaRole-CyYxEA1svxeL`

**使用箇所**:
- mcp-grpc-bridge-dev
- mock-hplc-device-dev
- mock-centrifuge-device-dev
- mock-pipette-device-dev

**必要な権限追加** (Task 2.4):
- ALBからのLambda呼び出し権限
- VPC関連権限（Phase 4用）

---

## 📝 設定ファイル

### .phase3-config
```bash
API_URL="https://82lhs2drfk.execute-api.us-west-2.amazonaws.com/dev"  # ❌ 存在しないAPI Gateway
LAMBDA_ROLE_ARN="arn:aws:iam::590183741681:role/sila2-phase3-architecture-compl-DeviceApiLambdaRole-Vzpa37vA8SAx"
REGION="us-west-2"
ACCOUNT_ID="590183741681"
STACK_NAME="sila2-lab-automation-phase3-infra"
ECR_URI=590183741681.dkr.ecr.us-west-2.amazonaws.com/bedrock-agentcore-sila2_runtime_phase3
DEPLOYMENT_STATUS=completed
DEPLOYMENT_TIME="Mon Nov 24 06:13:58 UTC 2025"
LAMBDA_FUNCTIONS="sila2-mock-device-lambda-dev	sila2-agentcore-runtime-dev"
```

**修正必要箇所**:
- `API_URL`: 82lhs2drfkを削除
- `LAMBDA_FUNCTIONS`: 実際の関数名と不一致

---

## ✅ 削除可能リソースリスト

1. **API Gateway `82lhs2drfk`**: 既に存在しない（設定ファイルから削除のみ）
2. **API Gateway `ib5h74dpr1`**: ALB移行完了後に削除
3. **Lambda Layer `grpc-layer` (v1)**: Python 3.9用、不要

---

## ⚠️ 注意事項

1. **API Gateway ib5h74dpr1**: 現在テスト用として使用中の可能性あり。削除前に使用状況を再確認
2. **IAM Role**: 複数Lambda関数で共有。権限変更時は影響範囲に注意
3. **CloudFormationスタック**: 削除時は依存リソースの順序に注意

---

## 🎯 次のアクション

- [x] Task 0.1: リソース棚卸し完了
- [ ] Task 0.2: gRPC実装状況確認
- [ ] Task 1.1: `.phase3-config`から82lhs2drfk削除
- [ ] Task 2.x: ALB作成後、ib5h74dpr1削除
