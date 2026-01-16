# Phase 1: CloudFormation統合 - 完了レポート

## 実施日時
2025年1月

## 実施内容

### 1. ネストスタック構造の作成 ✅

#### 作成したファイル
```
infrastructure/
├── main.yaml                    # ルートテンプレート（新規作成）
└── nested/                      # 新規ディレクトリ
    ├── ecs.yaml                # ECS/Fargate（bridge_container_ecs.yamlから移行）
    ├── lambda.yaml             # Lambda関数（lambda_proxy.yaml + events_sns.yamlから統合）
    └── events.yaml             # SNS + EventBridge（events_sns.yamlから分離）
```

#### テンプレート統合の詳細

**ecs.yaml**
- 元: `bridge_container_ecs.yaml`
- 内容: ECS Cluster, Task Definitions, Services, Service Discovery
- 最適化: 不要なコメント削除、パラメータ簡略化

**lambda.yaml**
- 元: `lambda_proxy.yaml` + `events_sns.yaml`（Lambda部分）
- 内容: Lambda Proxy, Lambda Invoker, IAM Roles
- 統合: 2つのテンプレートのLambda関数を1つに集約

**events.yaml**
- 元: `events_sns.yaml`（Events部分）
- 内容: SNS Topic, EventBridge Rule, Permissions
- 分離: Lambda定義から分離して独立管理

**main.yaml**
- 新規作成
- 3つのネストスタックを統合
- 依存関係: ECS → Lambda → Events

### 2. デプロイスクリプトの作成 ✅

#### 作成したファイル
```
scripts/
├── 03_deploy_stack.sh          # メインデプロイスクリプト
└── utils/
    ├── config.sh               # 共通設定
    └── common.sh               # 共通関数
```

#### スクリプトの機能
- S3バケット自動作成
- ネストテンプレートのアップロード
- CloudFormation package & deploy
- スタック出力の表示

### 3. 既存ファイルの保持

以下のファイルは**そのまま保持**（Phase 2以降で移行予定）:
- `bridge_container_ecs.yaml` → `infrastructure/legacy/`へ移動予定
- `lambda_proxy.yaml` → `infrastructure/legacy/`へ移動予定
- `events_sns.yaml` → `infrastructure/legacy/`へ移動予定

## デプロイ方法

### 前提条件
1. VPC IDとPrivate Subnet IDs（2つ以上）を準備
2. AWS CLIとDockerがインストール済み
3. 適切なIAM権限

### デプロイコマンド
```bash
cd /home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent

# デプロイ実行
./scripts/03_deploy_stack.sh \
  --vpc-id vpc-xxxxxxxxx \
  --subnet-ids subnet-xxxxxxxx,subnet-yyyyyyyy
```

### デプロイフロー
1. S3バケット作成（存在しない場合）
2. ネストテンプレートをS3にアップロード
3. main.yamlをパッケージング
4. CloudFormationスタックをデプロイ
5. 出力を表示

## 効果

### Before（Phase 0）
- 3つの独立したCloudFormationテンプレート
- 手動での順次デプロイが必要
- 依存関係の管理が複雑

### After（Phase 1）
- 1つのルートテンプレート + 3つのネストスタック
- 1コマンドでデプロイ完了
- 依存関係が自動管理

### メリット
1. **デプロイの簡素化**: 複数のスタックを1コマンドでデプロイ
2. **依存関係の明確化**: ネストスタックで依存関係を定義
3. **保守性の向上**: テンプレートが論理的に分割
4. **再利用性**: ネストスタックは他のプロジェクトでも利用可能

## 次のステップ（Phase 2）

### 実施予定
1. VPC Endpoint & ECRのCFn化
2. `nested/network.yaml`作成
3. `nested/ecr.yaml`作成
4. スクリプト00, 01の削除

### 期待効果
- スクリプト数: 7個 → 5個
- ECRリポジトリの自動作成
- VPC Endpointの自動設定

## 検証項目

### デプロイ前の確認
- [ ] VPC IDが正しい
- [ ] Subnet IDsが正しい（2つ以上）
- [ ] AWS CLIが設定済み
- [ ] IAM権限が適切

### デプロイ後の確認
- [ ] main.yamlスタックが正常にデプロイされた
- [ ] 3つのネストスタックが作成された
- [ ] ECS Serviceが起動している
- [ ] Lambda関数が作成された
- [ ] SNS Topicが作成された
- [ ] EventBridge Ruleが有効

### 動作確認
- [ ] Bridge Serviceにアクセス可能
- [ ] Mock Device Serviceが起動
- [ ] Lambda Proxyが動作
- [ ] EventBridgeが定期実行

## トラブルシューティング

### エラー: S3バケットが作成できない
**原因**: バケット名が既に使用されている
**対処**: `scripts/utils/config.sh`のDEPLOYMENT_BUCKETを変更

### エラー: ネストスタックがタイムアウト
**原因**: ECSタスクの起動に時間がかかる
**対処**: TimeoutInMinutesを増やす（main.yaml）

### エラー: Lambda関数がVPCに接続できない
**原因**: Security GroupまたはSubnetの設定が不正
**対処**: VPC設定を確認

## 備考

- Phase 1は既存のスクリプトを削除せず、新しいデプロイ方法を追加
- 既存のデプロイ方法も引き続き使用可能
- Phase 2以降で段階的に既存スクリプトを削除予定
