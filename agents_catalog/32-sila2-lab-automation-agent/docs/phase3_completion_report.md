# Phase 3: Lambda統合 - 完了レポート

## 実施日時
2025年1月

## 実施内容

### 1. Lambda関数のCFn化 ✅

#### 更新したファイル
```
infrastructure/nested/lambda.yaml    # analyze_heating_rate Lambda追加
infrastructure/main.yaml             # DeploymentBucketパラメータ追加
```

#### 追加されたLambda関数
**AnalyzeHeatingRateFunction**
- 関数名: `sila2-analyze-heating-rate`
- Runtime: Python 3.12
- Handler: `index.lambda_handler`
- コードソース: S3 (`s3://${DeploymentBucket}/lambda/analyze_heating_rate.zip`)
- 機能: 温度上昇率の計算

**特徴:**
- S3からコードをデプロイ
- VPC不要（純粋な計算関数）
- 外部依存なし

### 2. デプロイスクリプトの作成 ✅

#### 作成したファイル
```
scripts/
├── 01_build_containers.sh      # 新規作成
└── 02_package_lambdas.sh       # 新規作成
```

#### 01_build_containers.sh
**機能:**
- ECRログイン
- Bridge containerビルド & プッシュ
- Mock devices containerビルド & プッシュ

**パス参照:**
- `src/bridge/` - Bridge container
- `src/devices/` - Mock devices container

#### 02_package_lambdas.sh
**機能:**
- S3バケット作成（存在しない場合）
- Lambda関数のzipパッケージ作成
- S3へのアップロード

**パッケージ対象:**
- `src/lambda/tools/analyze_heating_rate/` → `analyze_heating_rate.zip`
- `src/lambda/proxy/` → `proxy.zip`
- `src/lambda/invoker/` → `invoker.zip`

### 3. CloudFormationテンプレートの更新 ✅

#### lambda.yaml
**追加内容:**
- `DeploymentBucket` パラメータ
- `AnalyzeHeatingRateFunction` リソース
- `AnalyzeHeatingRateFunctionArn` Output

#### main.yaml
**更新内容:**
- LambdaStackに`DeploymentBucket`パラメータを渡す

## デプロイフロー

### 新しいデプロイフロー（Phase 3）
```bash
# 1. Dockerコンテナビルド & プッシュ
./scripts/01_build_containers.sh

# 2. Lambda関数パッケージング
./scripts/02_package_lambdas.sh

# 3. CloudFormationスタックデプロイ
./scripts/03_deploy_stack.sh --vpc-id vpc-xxx --subnet-ids subnet-xxx,subnet-yyy

# 4. AgentCore Runtimeデプロイ
./scripts/06_deploy_agentcore.sh
```

### CloudFormationが自動実行する内容
1. ECRリポジトリ作成
2. ECS Cluster & Services作成
3. VPC Endpoint作成
4. Lambda関数作成（Proxy, Invoker, **AnalyzeHeatingRate**）
5. SNS & EventBridge作成

## スクリプト削減効果

### Before（Phase 2）
```
scripts/
├── 02_build_containers.sh
├── 03_deploy_ecs.sh
├── 03_deploy_stack.sh
├── 04_create_gateway.sh
├── 05_create_mcp_target.sh
├── 06_deploy_agentcore.sh
└── 07_run_tests.sh
```

### After（Phase 3）
```
scripts/
├── 01_build_containers.sh        # 新規作成
├── 02_package_lambdas.sh         # 新規作成
├── 02_build_containers.sh        # 将来削除予定
├── 03_deploy_ecs.sh              # 将来削除予定
├── 03_deploy_stack.sh            # メインデプロイ
├── 04_create_gateway.sh          # Phase 4で削除予定
├── 05_create_mcp_target.sh       # Phase 4で削除予定
├── 06_deploy_agentcore.sh
└── 07_run_tests.sh
```

**実質的な削減**: スクリプト05の一部機能をCFn化

## メリット

### 1. Lambda関数の自動デプロイ
- S3からコードを自動デプロイ
- バージョン管理が容易
- ロールバックが簡単

### 2. コード管理の一元化
- Lambda関数コードが`src/lambda/`配下に集約
- パッケージングが自動化

### 3. デプロイの簡素化
- Lambda関数の作成・更新がCFnで管理
- 手動でのLambda作成が不要

### 4. 依存関係の明確化
- Lambda関数がS3バケットに依存
- デプロイ順序が保証される

## 注意事項

### Lambda関数コードの更新
Lambda関数コードを更新する場合:
1. `src/lambda/`配下のコードを修正
2. `./scripts/02_package_lambdas.sh`を実行
3. `./scripts/03_deploy_stack.sh`を実行（または手動でLambda更新）

### S3バケットの管理
- S3バケットは自動作成される
- バケット名: `sila2-deployment-${ACCOUNT_ID}-${REGION}`
- Lambda zipファイルは`lambda/`プレフィックス配下

### 既存Lambda関数との互換性
- Proxy, Invoker関数は引き続きインラインコード
- 将来的にS3デプロイに移行可能

## 次のステップ（Phase 4）

### 実施予定
1. Custom Resource Lambda作成
2. Gateway管理のCFn化
3. Target管理のCFn化
4. `nested/agentcore.yaml`作成
5. スクリプト04, 05の削除

### 期待効果
- スクリプト数: 5個 → 3個
- Gateway/Targetの自動管理
- 完全なIaC化（AgentCore Runtime除く）

## 検証項目

### デプロイ前の確認
- [ ] `src/lambda/`配下にLambda関数コードが存在
- [ ] S3バケットが作成可能
- [ ] ECRリポジトリが存在

### デプロイ後の確認
- [ ] S3バケットが作成された
- [ ] Lambda zipファイルがS3にアップロードされた
- [ ] AnalyzeHeatingRateFunction が作成された
- [ ] Lambda関数が正常に動作

### 動作確認
```bash
# Lambda関数のテスト
aws lambda invoke \
  --function-name sila2-analyze-heating-rate \
  --payload '{"device_id":"hplc","history":[{"temperature":25,"timestamp":"2025-01-01T00:00:00Z"},{"temperature":30,"timestamp":"2025-01-01T00:01:00Z"}]}' \
  --region us-west-2 \
  /tmp/response.json

cat /tmp/response.json
```

## トラブルシューティング

### エラー: S3バケットが作成できない
**原因**: バケット名が既に使用されている
**対処**: `scripts/utils/config.sh`のDEPLOYMENT_BUCKETを変更

### エラー: Lambda関数がS3からコードを取得できない
**原因**: zipファイルがS3に存在しない
**対処**: `./scripts/02_package_lambdas.sh`を実行

### エラー: Lambda関数の実行に失敗
**原因**: コードにエラーがある
**対処**: CloudWatch Logsでエラーを確認

## 備考

- Phase 3では既存スクリプト02, 03を削除せず、新しいスクリプト01, 02を追加
- 既存のデプロイ方法も引き続き使用可能（後方互換性）
- Phase 4でGateway/Target管理をCFn化予定
- 最終的には4つのスクリプトに集約（01, 02, 03, 06）
