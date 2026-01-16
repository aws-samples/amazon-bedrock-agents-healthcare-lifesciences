# Phase 2: VPC Endpoint & ECR の CFn化 - 完了レポート

## 実施日時
2025年1月

## 実施内容

### 1. 新規テンプレートの作成 ✅

#### 作成したファイル
```
infrastructure/nested/
├── ecr.yaml        # ECRリポジトリ（新規作成）
└── network.yaml    # VPC Endpoint（新規作成）
```

#### ecr.yaml
**機能:**
- sila2-bridge リポジトリ
- sila2-mock-devices リポジトリ
- イメージスキャン有効化
- ライフサイクルポリシー（最新10イメージ保持）

**置き換え対象:**
- `scripts/01_setup_infrastructure.sh`

#### network.yaml
**機能:**
- Bedrock AgentCore VPC Endpoint
- Interface型エンドポイント
- Private DNS有効化
- セキュリティグループ設定

**置き換え対象:**
- `scripts/00_setup_vpc_endpoint.sh`

### 2. main.yamlの更新 ✅

#### 追加されたスタック
```yaml
Resources:
  ECRStack:           # 新規追加（最初に実行）
  ECSStack:           # ECRStackに依存
  NetworkStack:       # 新規追加（ECSStackに依存）
  LambdaStack:        # NetworkStackに依存
  EventsStack:        # LambdaStackに依存
```

#### 依存関係
```
ECR → ECS → Network → Lambda → Events
```

#### 新規Output
- `BridgeRepositoryUri`: Bridge用ECRリポジトリURI
- `MockDevicesRepositoryUri`: Mock Devices用ECRリポジトリURI
- `VpcEndpointId`: VPC Endpoint ID

### 3. 既存ファイルの移動 ✅

#### スクリプト
```bash
scripts/00_setup_vpc_endpoint.sh  → scripts/legacy/
scripts/01_setup_infrastructure.sh → scripts/legacy/
```

#### CloudFormationテンプレート
```bash
infrastructure/bridge_container_ecs.yaml → infrastructure/legacy/
infrastructure/lambda_proxy.yaml         → infrastructure/legacy/
infrastructure/events_sns.yaml           → infrastructure/legacy/
```

## スクリプト削減効果

### Before（Phase 1）
```
scripts/
├── 00_setup_vpc_endpoint.sh      # 削除
├── 01_setup_infrastructure.sh    # 削除
├── 02_build_containers.sh
├── 03_deploy_ecs.sh
├── 03_deploy_stack.sh            # Phase 1で追加
├── 04_create_gateway.sh
├── 05_create_mcp_target.sh
├── 06_deploy_agentcore.sh
└── 07_run_tests.sh
```

### After（Phase 2）
```
scripts/
├── 02_build_containers.sh
├── 03_deploy_ecs.sh              # 将来削除予定
├── 03_deploy_stack.sh            # メインデプロイ
├── 04_create_gateway.sh          # 将来削除予定
├── 05_create_mcp_target.sh       # 将来削除予定
├── 06_deploy_agentcore.sh
├── 07_run_tests.sh
└── legacy/
    ├── 00_setup_vpc_endpoint.sh
    └── 01_setup_infrastructure.sh
```

**削減数**: 2スクリプト（00, 01）

## デプロイフロー

### 新しいデプロイフロー
```bash
# 1. ECRリポジトリ作成（CloudFormation）
# 2. Dockerイメージビルド & プッシュ（手動）
./scripts/02_build_containers.sh

# 3. 全スタックデプロイ（CloudFormation）
./scripts/03_deploy_stack.sh --vpc-id vpc-xxx --subnet-ids subnet-xxx,subnet-yyy
```

### CloudFormationが自動実行する内容
1. ECRリポジトリ作成
2. ECS Cluster & Services作成
3. VPC Endpoint作成
4. Lambda関数作成
5. SNS & EventBridge作成

## メリット

### 1. インフラのコード化
- ECRリポジトリがIaCで管理
- VPC Endpointがバージョン管理下に

### 2. 自動ロールバック
- デプロイ失敗時に自動ロールバック
- 手動クリーンアップ不要

### 3. 依存関係の明確化
- ECR → ECS → Network の順序が保証
- 並列実行可能な部分は自動最適化

### 4. 再現性の向上
- 同じテンプレートで同じ環境を再現
- 環境差異の削減

## 注意事項

### ECRリポジトリの既存確認
既にECRリポジトリが存在する場合:
1. CloudFormationはエラーを返す
2. 既存リポジトリをインポートするか
3. 既存リポジトリを削除してから実行

### VPC Endpointの既存確認
既にVPC Endpointが存在する場合:
1. CloudFormationはエラーを返す
2. 既存エンドポイントを削除してから実行
3. または手動で管理を継続

## 次のステップ（Phase 3）

### 実施予定
1. Lambda関数コードのS3デプロイ
2. `nested/lambda.yaml`の拡張
3. analyze-heating-rate Lambda追加
4. Lambda Layer管理

### 期待効果
- スクリプト05の一部をCFn化
- Lambda関数の自動デプロイ
- コード管理の一元化

## 検証項目

### デプロイ前の確認
- [ ] 既存ECRリポジトリの有無確認
- [ ] 既存VPC Endpointの有無確認
- [ ] VPC IDとSubnet IDsの準備

### デプロイ後の確認
- [ ] ECRStackが正常にデプロイされた
- [ ] NetworkStackが正常にデプロイされた
- [ ] ECRリポジトリが作成された（2つ）
- [ ] VPC Endpointが作成された
- [ ] VPC Endpointが"available"状態

### 動作確認
- [ ] ECRにイメージをプッシュ可能
- [ ] VPC Endpoint経由でBedrock AgentCoreにアクセス可能
- [ ] Lambda関数がVPC Endpoint経由で通信可能

## トラブルシューティング

### エラー: ECRリポジトリが既に存在
**原因**: 既存のECRリポジトリと名前が重複
**対処**: 
```bash
# 既存リポジトリを削除
aws ecr delete-repository --repository-name sila2-bridge --force
aws ecr delete-repository --repository-name sila2-mock-devices --force
```

### エラー: VPC Endpointが既に存在
**原因**: 既存のVPC Endpointと重複
**対処**:
```bash
# 既存エンドポイントを削除
aws ec2 delete-vpc-endpoints --vpc-endpoint-ids vpce-xxxxx
```

### エラー: Security Groupが見つからない
**原因**: ECSStackのOutputが正しく参照されていない
**対処**: ECSStackが正常にデプロイされているか確認

## 備考

- Phase 2では既存スクリプトを削除せず、legacyフォルダに移動
- 既存のデプロイ方法も引き続き使用可能（後方互換性）
- Phase 3以降で段階的に残りのスクリプトを削減予定
- ECRとNetworkのテンプレートは独立しており、他プロジェクトでも再利用可能
