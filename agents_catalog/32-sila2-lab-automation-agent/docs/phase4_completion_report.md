# Phase 4完了レポート: Custom Resource統合

## 実施日
2025年1月

## 概要
Gateway/Target管理をCustom ResourceでCloudFormation化し、スクリプト04と05を削除しました。

## 実施内容

### 1. Custom Resource Lambda作成
**ファイル**: `src/lambda/custom_resources/agentcore_manager/index.py`

**機能**:
- Gateway作成/削除
- Target作成/削除
- IAM権限管理
- Lambda権限管理

**主要機能**:
```python
def handle_gateway(event, context):
    # Gateway作成時にIAM権限とTrust Policyを自動設定
    # Gateway削除時にクリーンアップ

def handle_target(event, context):
    # Target作成時にLambda権限を自動付与
    # Target削除時にクリーンアップ
```

### 2. AgentCore CloudFormationテンプレート作成
**ファイル**: `infrastructure/nested/agentcore.yaml`

**リソース**:
- `AgentCoreManagerFunction`: Custom Resource Lambda
- `AgentCoreManagerRole`: Lambda実行ロール
- `Gateway`: AgentCore Gateway (Custom Resource)
- `BridgeTarget`: Bridge Container Target (Custom Resource)
- `AnalyzeHeatingRateTarget`: Heating Rate Analysis Target (Custom Resource)

**パラメータ**:
- `DeploymentBucket`: Lambda zipファイル格納バケット
- `ExecutionRoleArn`: Gateway実行ロール
- `ProxyFunctionArn`: Proxy Lambda ARN
- `AnalyzeHeatingRateFunctionArn`: Analyze Heating Rate Lambda ARN

**出力**:
- `GatewayId`, `GatewayArn`, `GatewayUrl`
- `BridgeTargetId`, `AnalyzeHeatingRateTargetId`

### 3. メインスタック更新
**ファイル**: `infrastructure/main.yaml`

**変更点**:
- `AgentCoreStack`を追加（LambdaStackに依存）
- Gateway/Target情報をOutputsに追加

### 4. スクリプト更新

#### 02_package_lambdas.sh
- `agentcore_manager` Custom Resourceのパッケージング追加

#### 04_deploy_agentcore.sh（新規作成）
- CloudFormation OutputsからGateway情報取得
- agentcore CLIでRuntime設定・デプロイ
- 旧スクリプト06の簡略版

#### 共通関数（utils/common.sh）
- `package_custom_resource()` 関数追加

### 5. レガシースクリプト移動
```bash
scripts/legacy/
  ├── 00_setup_vpc_endpoint.sh
  ├── 01_setup_infrastructure.sh
  ├── 04_create_gateway.sh        # 新規移動
  └── 05_create_mcp_target.sh     # 新規移動
```

## デプロイフロー

### Phase 4完了後のデプロイ手順
```bash
# 1. Dockerコンテナビルド & ECRプッシュ
./scripts/01_build_containers.sh

# 2. Lambda関数パッケージング & S3アップロード
./scripts/02_package_lambdas.sh

# 3. CloudFormationスタックデプロイ（Gateway/Target含む）
./scripts/03_deploy_stack.sh

# 4. AgentCore Runtimeデプロイ
./scripts/04_deploy_agentcore.sh
```

## スクリプト削減効果

### Before Phase 4
```
scripts/
  ├── 01_build_containers.sh
  ├── 02_package_lambdas.sh
  ├── 03_deploy_stack.sh
  ├── 04_create_gateway.sh        # 削除対象
  ├── 05_create_mcp_target.sh     # 削除対象
  └── 06_deploy_agentcore.sh
```

### After Phase 4
```
scripts/
  ├── 01_build_containers.sh
  ├── 02_package_lambdas.sh
  ├── 03_deploy_stack.sh
  └── 04_deploy_agentcore.sh      # 簡略化された新スクリプト
```

**削減**: 6スクリプト → 4スクリプト（33%削減）

## CloudFormationスタック構成

```
main.yaml (ルート)
├── ECRStack (ecr.yaml)
├── ECSStack (ecs.yaml)
├── NetworkStack (network.yaml)
├── LambdaStack (lambda.yaml)
├── EventsStack (events.yaml)
└── AgentCoreStack (agentcore.yaml)  # 新規追加
    ├── AgentCoreManagerFunction
    ├── Gateway (Custom Resource)
    ├── BridgeTarget (Custom Resource)
    └── AnalyzeHeatingRateTarget (Custom Resource)
```

## 利点

### 1. インフラのコード化
- Gateway/Target作成がCloudFormationで管理
- 自動ロールバック対応
- 再現性の向上

### 2. デプロイの簡素化
- スクリプト数削減（6→4）
- 手動操作の削減
- エラーハンドリングの改善

### 3. 保守性の向上
- IAM権限管理の自動化
- リソース依存関係の明確化
- スタック削除時の自動クリーンアップ

## 次のステップ

Phase 4完了により、CloudFormation統合計画の主要部分が完了しました。

### 残作業
- Phase 5（AgentCore Runtime CFn化）は保留
  - 理由: agentcore CLIの複雑性、費用対効果が低い
  - 結論: スクリプト04（旧06）はそのまま維持

### 最終構成
```
scripts/
  ├── 01_build_containers.sh      # Docker build & ECR push
  ├── 02_package_lambdas.sh       # Lambda packaging
  ├── 03_deploy_stack.sh          # CloudFormation deploy
  └── 04_deploy_agentcore.sh      # AgentCore Runtime
```

## 検証項目

### デプロイ検証
- [ ] 01_build_containers.sh 実行成功
- [ ] 02_package_lambdas.sh 実行成功
- [ ] 03_deploy_stack.sh 実行成功
- [ ] AgentCoreStack作成成功
- [ ] Gateway作成成功
- [ ] Target作成成功
- [ ] 04_deploy_agentcore.sh 実行成功

### 機能検証
- [ ] Gateway URLが正しく取得できる
- [ ] Target IDが正しく取得できる
- [ ] Lambda権限が正しく設定される
- [ ] AgentCore Runtimeが正常動作

### クリーンアップ検証
- [ ] スタック削除時にGateway削除
- [ ] スタック削除時にTarget削除
- [ ] IAM権限のクリーンアップ

## まとめ

Phase 4の完了により、以下を達成しました：

1. ✅ Gateway/Target管理のCloudFormation化
2. ✅ Custom Resource Lambdaの実装
3. ✅ スクリプト数の削減（6→4）
4. ✅ デプロイフローの簡素化
5. ✅ インフラのコード化完了

**Phase 1-4の統合により、当初の目標である「7スクリプト→4スクリプト」を達成しました。**
