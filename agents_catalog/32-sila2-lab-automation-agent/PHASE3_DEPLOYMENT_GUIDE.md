# SiLA2 Lab Automation Agent - Phase 3 デプロイガイド

## 概要

フェーズ3では、フェーズ2で完了した基盤に機能追加を行い、完全なSiLA2ラボ自動化エージェントを構築します。

## 段階的デプロイ手順

### Step 1: インフラストラクチャデプロイ
```bash
./deploy-phase3-step1-infra.sh
```
- CloudFormationテンプレートをデプロイ
- 必要なAWSリソースを作成
- 設定情報を `.phase3-config` に保存

### Step 2: コードデプロイ
```bash
./deploy-phase3-step2-code.sh
```
- Python環境をセットアップ
- Lambda関数コードを更新
- メインエントリーポイントを作成

### Step 3: テスト実行
```bash
./deploy-phase3-step3-test.sh
```
- Lambda関数の動作確認
- API Gatewayのテスト
- 基本機能の検証

### Step 4: AgentCoreセットアップ
```bash
./deploy-phase3-step4-agentcore.sh
```
- AgentCore設定ファイル作成
- ECRリポジトリ準備
- エージェント用メインファイル作成

### Step 5: 最終統合
```bash
./deploy-phase3-final.sh
```
- AgentCoreデプロイ実行
- 最終テストと検証
- デプロイサマリー表示

## 一括デプロイ（上級者向け）

全ステップを一度に実行する場合：
```bash
./deploy-phase3-complete.sh
```

## 前提条件

- フェーズ2が正常に完了していること
- Python 3.10.12がpyenvで利用可能
- AWS CLIが設定済み
- 必要なAWS権限を持っていること

## トラブルシューティング

### 設定ファイルが見つからない
```bash
# Step 1から再実行
./deploy-phase3-step1-infra.sh
```

### Lambda関数が見つからない
```bash
# AWS CLIでLambda関数を確認
aws lambda list-functions --region us-west-2 --query 'Functions[?contains(FunctionName, `sila2`)].FunctionName'
```

### AgentCoreデプロイエラー
```bash
# bedrock-agentcoreの再インストール
pip install --upgrade bedrock-agentcore
```

## 設定ファイル

- `.phase3-config`: デプロイ設定情報
- `.bedrock_agentcore_phase3.yaml`: AgentCore設定
- `main_agentcore_phase3.py`: AgentCore用メインファイル

## 機能

Phase 3で追加される機能：
- デバイス一覧表示
- デバイス状態確認
- 測定開始/停止
- デバイスコマンド実行
- 測定データ取得
- プロトコルブリッジ機能

## 次のステップ

デプロイ完了後：
1. AgentCoreエージェントとの対話テスト
2. 実際のSiLA2デバイスとの接続テスト
3. 本番環境への展開準備