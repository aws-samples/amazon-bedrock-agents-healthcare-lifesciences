# 影響範囲分析レポート
**作成日**: 2025-01-27  
**タスク**: Task 0.4 - Phase 3 → Phase 3改善版の影響範囲分析  
**ステータス**: ✅ 完了

---

## 📊 影響範囲サマリー

### 変更対象コンポーネント

| コンポーネント | 変更内容 | 影響度 | ダウンタイム |
|---|---|---|---|
| API Gateway (ib5h74dpr1) | 削除 | 🟡 中 | なし |
| ALB | 新規作成 | 🟢 低 | なし |
| MCP-gRPC Bridge Lambda | gRPCクライアント実装 | 🔴 高 | あり (5分) |
| Mock Device Lambda (3個) | gRPCサーバー有効化 | 🟡 中 | あり (5分) |
| .phase3-config | 設定更新 | 🟢 低 | なし |

---

## 🔍 詳細影響分析

### 1. MCP-gRPC Bridge Lambda
**影響度**: 🔴 **HIGH**

#### 変更内容
- boto3 Lambda Invoke → gRPC呼び出しに変更
- 環境変数 `ALB_ENDPOINT` 追加
- gRPCクライアント実装

#### 影響範囲
- **AgentCore Gateway**: MCP-gRPC Bridgeを呼び出す全てのツール
- **既存機能**: デバイスステータス取得、コマンド実行

#### リスク
- gRPC通信エラー時のフォールバック未実装
- タイムアウト設定が不適切な場合、レスポンス遅延

#### 軽減策
- 段階的デプロイ（Blue/Green）
- 詳細なエラーログ
- ロールバック手順準備

---

### 2. Mock Device Lambda (HPLC, Centrifuge, Pipette)
**影響度**: 🟡 **MEDIUM**

#### 変更内容
- 環境変数 `GRPC_ENABLED=true` 設定
- gRPCサーバーモード有効化
- ALBからの呼び出しに対応

#### 影響範囲
- **既存機能**: 全てのデバイス操作
- **テストスクリプト**: 直接Lambda呼び出しを使用しているテスト

#### リスク
- gRPCサーバー起動失敗
- Lambda実行時間増加（gRPCサーバー初期化）

#### 軽減策
- 既存のLambdaモードを残す（環境変数で切り替え）
- 包括的なユニットテスト

---

### 3. API Gateway (ib5h74dpr1)
**影響度**: 🟡 **MEDIUM**

#### 変更内容
- ALB移行完了後に削除

#### 影響範囲
- **テスト用エンドポイント**: 現在使用中の可能性
- **ドキュメント**: API Gateway URLを参照している箇所

#### リスク
- テストスクリプトが動作しなくなる

#### 軽減策
- 削除前に使用状況を再確認
- テストスクリプトをALBエンドポイントに更新

---

### 4. Application Load Balancer (新規)
**影響度**: 🟢 **LOW**

#### 変更内容
- 新規作成

#### 影響範囲
- なし（新規リソース）

#### リスク
- VPC設定ミス
- セキュリティグループ設定ミス

#### 軽減策
- CloudFormationテンプレートでIaC管理
- デプロイ前の設定レビュー

---

## ⏱️ ダウンタイム見積もり

### 段階的デプロイシナリオ

#### Phase 1: インフラ準備 (ダウンタイムなし)
- **所要時間**: 30分
- **作業内容**:
  - ALB作成
  - ターゲットグループ作成
  - セキュリティグループ設定

#### Phase 2: Lambda更新 (ダウンタイム: 5分)
- **所要時間**: 10分
- **ダウンタイム**: 5分
- **作業内容**:
  - Mock Device Lambda更新 (3個)
  - MCP-gRPC Bridge Lambda更新
  - 環境変数設定

#### Phase 3: 統合テスト (ダウンタイムなし)
- **所要時間**: 15分
- **作業内容**:
  - エンドツーエンドテスト
  - パフォーマンステスト

#### Phase 4: API Gateway削除 (ダウンタイムなし)
- **所要時間**: 5分
- **作業内容**:
  - API Gateway ib5h74dpr1 削除
  - 設定ファイル更新

**合計ダウンタイム**: **5分**  
**合計所要時間**: **60分**

---

## 🔄 ロールバック戦略

### シナリオ1: ALB作成失敗
**対応**: CloudFormationスタック削除のみ  
**所要時間**: 5分  
**影響**: なし

### シナリオ2: Lambda更新失敗
**対応**: Lambda関数を前バージョンに戻す  
**手順**:
```bash
aws lambda update-function-code \
  --function-name mcp-grpc-bridge-dev \
  --s3-bucket <backup-bucket> \
  --s3-key lambda/mcp-grpc-bridge-backup.zip
```
**所要時間**: 3分  
**影響**: 5分のダウンタイム

### シナリオ3: gRPC通信エラー
**対応**: 環境変数 `GRPC_ENABLED=false` に戻す  
**手順**:
```bash
aws lambda update-function-configuration \
  --function-name mock-hplc-device-dev \
  --environment Variables={GRPC_ENABLED=false}
```
**所要時間**: 2分  
**影響**: 既存機能に戻る

### シナリオ4: 完全ロールバック
**対応**: Phase 3アーキテクチャに戻す  
**手順**:
1. ALB削除
2. Lambda関数を前バージョンに戻す
3. API Gateway ib5h74dpr1 を再作成（必要に応じて）
**所要時間**: 15分  
**影響**: 15分のダウンタイム

---

## 📋 テストデータ準備計画

### 1. ユニットテスト用データ
```json
{
  "test_get_device_status": {
    "device_id": "HPLC-01",
    "action": "get_status"
  },
  "test_execute_command": {
    "device_id": "HPLC-01",
    "action": "start_analysis",
    "method": "standard",
    "volume": 20
  }
}
```

### 2. 統合テスト用データ
- エンドツーエンドシナリオ (10パターン)
- エラーケース (5パターン)
- 境界値テスト (3パターン)

### 3. パフォーマンステスト用データ
- 同時リクエスト数: 10, 50, 100
- リクエストサイズ: 1KB, 10KB, 100KB

---

## 🎯 段階的移行シナリオ

### Blue/Green デプロイ

#### Blue環境 (現行)
- API Gateway ib5h74dpr1
- boto3 Lambda Invoke

#### Green環境 (新規)
- ALB
- gRPC通信

#### 切り替え手順
1. Green環境構築 (ダウンタイムなし)
2. Green環境テスト (ダウンタイムなし)
3. トラフィック切り替え (ダウンタイム: 5分)
4. Blue環境削除 (ダウンタイムなし)

---

## ⚠️ リスク評価マトリクス

| リスク | 発生確率 | 影響度 | 優先度 | 軽減策 |
|---|---|---|---|---|
| gRPC通信エラー | 中 | 高 | 🔴 HIGH | 詳細なエラーログ、フォールバック実装 |
| Lambda実行時間増加 | 低 | 中 | 🟡 MEDIUM | パフォーマンステスト、タイムアウト調整 |
| ALB設定ミス | 低 | 高 | 🔴 HIGH | CloudFormation、設定レビュー |
| API Gateway削除ミス | 低 | 低 | 🟢 LOW | 削除前の使用状況確認 |
| VPC設定ミス | 低 | 中 | 🟡 MEDIUM | セキュリティグループレビュー |

---

## ✅ 承認チェックリスト

### 技術承認
- [x] アーキテクチャレビュー完了
- [x] セキュリティレビュー完了
- [x] コスト試算完了
- [ ] Tech Lead承認
- [ ] DevOps承認

### 運用承認
- [x] ダウンタイム見積もり完了
- [x] ロールバック手順準備完了
- [x] テストデータ準備計画完了
- [ ] 運用チーム承認

### ビジネス承認
- [x] コスト承認
- [x] スケジュール承認
- [ ] ステークホルダー承認

---

## 🎯 次のアクション

- [x] Task 0.4: 影響範囲分析完了
- [ ] Task Group 0 全体レビュー
- [ ] 実装承認取得
- [ ] Task Group 1 開始
