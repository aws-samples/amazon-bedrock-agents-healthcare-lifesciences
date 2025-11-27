# ALB採用決定レポート
**作成日**: 2025-01-27  
**タスク**: Task 0.3 - API Gateway gRPC統合の技術検証  
**決定**: ✅ **Application Load Balancer (ALB) を採用**

---

## 📊 技術検証結果

### Option A: API Gateway REST API + gRPC-JSON Transcoding
**評価**: ❌ 不採用

#### 制約事項
- API Gateway REST APIはHTTP/1.1のみサポート
- gRPCはHTTP/2が必須
- gRPC-JSON transcodingは追加の変換レイヤーが必要
- パフォーマンスオーバーヘッドが大きい

#### コスト
- API Gateway: $3.50/百万リクエスト
- 追加のtranscoding処理コスト

#### 結論
gRPCネイティブサポートなし。Phase 4での実機器接続に不適。

---

### Option B: Application Load Balancer + Lambda ✅ **採用**
**評価**: ✅ 採用

#### 利点
1. **HTTP/2ネイティブサポート**: gRPC Passthroughが可能
2. **Phase 4への移行が容易**: ターゲットグループ変更のみ
3. **VPC統合**: 実機器接続時のセキュアな通信
4. **柔軟なルーティング**: パスベース、ヘッダーベースルーティング
5. **ヘルスチェック**: gRPC対応のヘルスチェック機能

#### 制約事項
- 初期コストがAPI Gatewayより高い
- VPC内リソースが必要

#### コスト試算
- ALB: $0.0225/時間 ($16.20/月) + $0.008/LCU時間
- 想定トラフィック: 1,000リクエスト/日
- 月間コスト: 約$20-30

#### Phase 4移行パス
```
Phase 3改善版:
  MCP-gRPC Bridge → ALB → Lambda (Mock Device)

Phase 4:
  MCP-gRPC Bridge → ALB → ├─ Lambda (Mock) 10%
                           └─ VPC実機器 90%
```
**変更箇所**: ALBターゲットグループのみ  
**MCP-gRPC Bridgeのコード変更**: 不要 ✅

---

### Option C: API Gateway HTTP API + カスタムプロキシ
**評価**: ❌ 不採用

#### 制約事項
- API Gateway HTTP APIはgRPC Passthroughをサポートしない
- カスタムプロキシLambdaが必要（複雑性増加）
- HTTP/2サポートは限定的

#### 結論
実装複雑度が高く、Phase 4移行時の柔軟性に欠ける。

---

## 🎯 ALB採用の決定理由

### 1. Phase 4への移行容易性 (最重要)
- ターゲットグループ変更のみで実機器接続可能
- MCP-gRPC Bridgeのコード変更不要
- 段階的移行（Canary/Blue-Green）が容易

### 2. gRPCネイティブサポート
- HTTP/2 Passthrough
- SiLA2プロトコル準拠の通信が可能
- パフォーマンスオーバーヘッドなし

### 3. 長期的なコスト効率
- Phase 4で実機器接続時、追加のインフラ変更不要
- 運用コストの削減

### 4. セキュリティ
- VPC内通信によるセキュアな実機器接続
- SSL/TLS終端

---

## 📋 ALB設定仕様

### 基本設定
```yaml
Type: application
Scheme: internal  # VPC内部のみアクセス
IpAddressType: ipv4
HTTP/2: Enabled
```

### リスナー設定
```yaml
Protocol: HTTPS
Port: 443
DefaultAction: forward to target-group
```

### ターゲットグループ設定
```yaml
TargetType: lambda
Protocol: HTTP
ProtocolVersion: GRPC
HealthCheck:
  Protocol: HTTP
  Path: /grpc.health.v1.Health/Check
  Interval: 30s
  Timeout: 5s
  HealthyThreshold: 2
  UnhealthyThreshold: 2
```

### ルーティングルール
```yaml
Rules:
  - Condition: path-pattern /sila2.SiLA2Device/*
    Action: forward to mock-device-target-group
```

---

## 💰 コスト比較

| 項目 | API Gateway | ALB | 差分 |
|---|---|---|---|
| 基本料金 | $0 | $16.20/月 | +$16.20 |
| リクエスト料金 | $3.50/百万 | $0.008/LCU | 変動 |
| 月間想定 (1,000req/日) | $0.11 | $20-30 | +$20 |
| Phase 4移行コスト | 高 (再実装) | 低 (設定変更のみ) | - |

**結論**: 初期コストは高いが、Phase 4移行を考慮すると長期的にコスト効率が良い。

---

## ✅ 受け入れ基準

- [x] HTTP/2サポート確認
- [x] gRPC Passthrough可能性確認
- [x] Lambda統合可能性確認
- [x] Phase 4移行パス明確化
- [x] コスト試算完了
- [x] セキュリティ要件確認

---

## 🎯 次のアクション

- [x] Task 0.3: ALB採用決定
- [ ] Task 2.1: ALB作成・設定
- [ ] Task 2.2: ターゲットグループ設定
- [ ] Task 2.3: リスナールール設定
