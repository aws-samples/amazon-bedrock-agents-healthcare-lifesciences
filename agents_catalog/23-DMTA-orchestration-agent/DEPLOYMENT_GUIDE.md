# DMTA Orchestration Agent - 段階的デプロイガイド

## 📋 デプロイ手順

### Step 1: 基本機能のデプロイ
```bash
./deploy-step1.sh
```
- DMTA Agent基本機能をデプロイ
- Lambda関数、DynamoDB、S3バケット作成
- Knowledge Baseなしで動作確認

### Step 2: Knowledge Base設定
```bash
./setup-knowledge-base.sh
```
- S3バケット作成
- Knowledge Baseデータ（3つのプロジェクト）アップロード
- 手動設定手順の表示

#### 手動設定（AWS Console）
1. **Bedrock Console** → **Knowledge bases** → **Create knowledge base**
2. **設定項目**:
   - Name: `DMTA-Knowledge-Base`
   - Data source: S3
   - S3 URI: `s3://dmta-kb-xxxxx/projects/`
   - Embedding model: Amazon Titan Embeddings G1 - Text
3. **Knowledge Base ID**をメモ（例: `KB123456789`）

### Step 3: Knowledge BaseとAgentの連携
```bash
./deploy-step3.sh <KNOWLEDGE_BASE_ID>
```
- Knowledge BaseをAgentに関連付け
- Agent準備とデプロイ完了

### Step 4: 動作確認
```bash
python3 test_agent.py
```
- Knowledge Base統合テスト
- DMTA Workflow動作確認

## 🔧 各ステップの詳細

### Step 1で作成されるリソース
- ✅ Bedrock Agent (基本機能)
- ✅ Lambda Functions (4つ)
- ✅ DynamoDB Tables (3つ)
- ✅ S3 Bucket (実験データ用)

### Step 2で作成されるリソース
- ✅ S3 Bucket (Knowledge Base用)
- ✅ Knowledge Baseデータファイル (3つ)

### Step 3で設定される機能
- ✅ Knowledge Base ↔ Agent連携
- ✅ 過去プロジェクト参照機能

## 📊 完成後の機能

### 🎯 DMTA Workflow
1. **Plan**: Knowledge Base参照でプロジェクト計画作成
2. **Design**: 獲得関数によるバリアント設計
3. **Make-Test**: FactorX実験データ生成
4. **Analyze**: ガウシアンプロセス解析

### 📚 Knowledge Base機能
- 過去の類似プロジェクト検索
- ベストプラクティス抽出
- 成功要因分析
- リスク軽減戦略

## 🚨 トラブルシューティング

### Step 1失敗時
```bash
aws cloudformation describe-stack-events --stack-name dmta-orchestration-agent
```

### Step 2失敗時
- S3バケット名の重複確認
- AWS権限の確認

### Step 3失敗時
- Knowledge Base IDの確認
- Agent IDの確認
- Bedrock権限の確認

## 📝 設定ファイル
- `.kb-bucket-name`: Knowledge Base S3バケット名
- `knowledge-base/`: ダミーデータファイル
- `test_agent.py`: 統合テストスクリプト