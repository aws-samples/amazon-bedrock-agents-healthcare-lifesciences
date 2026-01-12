# デプロイ最適化統合計画

## 現状分析

### 問題点
1. **スクリプト最適化計画**: 7スクリプトを共通関数で最適化（58%削減）
2. **CloudFormation統合計画**: CFnネストスタックで統合、スクリプト3つに削減
3. **整合性の問題**: 2つの計画が**矛盾**している

### 矛盾点
- スクリプト最適化: 既存スクリプトを改善
- CFn統合: スクリプトをCFnに置き換え
- **結論**: スクリプト最適化は**不要**（CFn化するため）

## 統合アプローチ（推奨）

### 前提条件
**このデプロイ最適化計画は、FOLDER_STRUCTURE_PLAN.md実施後の新しいフォルダ構成を前提としています。**

新フォルダ構成:
```
src/
  bridge/          # 旧 bridge_container
  devices/         # 旧 mock_devices
  lambda/          # 旧 lambda
  proto/           # 旧 proto
```

### 最終目標
```
現状: 7スクリプト（00-06）+ 3 CFnテンプレート
↓
最終: 3スクリプト + 1 CFnテンプレート（ネスト構造）
```

### 最終構成
```
scripts/
  01_build_containers.sh    # Docker build & ECR push
  02_package_lambdas.sh     # Lambda zip作成
  03_deploy_stack.sh        # CloudFormation deploy
  04_deploy_agentcore.sh    # agentcore CLI（CFn化困難）
  utils/
    common.sh
    config.sh               # 設定値集約

infrastructure/
  main.yaml                 # ルートテンプレート
  nested/
    network.yaml           # VPC Endpoint
    ecr.yaml              # ECRリポジトリ
    ecs.yaml              # ECS/Fargate
    lambda.yaml           # 全Lambda関数
    events.yaml           # SNS + EventBridge
    agentcore.yaml        # Gateway/Target（Custom Resource）
```

## 段階的実装計画

### Phase 1: CloudFormation統合（最優先）
**目標**: 既存3テンプレートをネストスタックに統合

**作業内容**:
1. `infrastructure/nested/` ディレクトリ作成
2. 既存テンプレートを分割・移動
   - `bridge_container_ecs_no_alb.yaml` → `ecs.yaml`
   - `lambda_proxy.yaml` → `lambda.yaml`（一部）
   - `phase6-cfn.yaml` → `lambda.yaml` + `events.yaml`
3. `main.yaml` 作成（ネストスタック参照）
4. `scripts/03_deploy_stack.sh` 作成

**削減スクリプト**: なし（まだ）
**期間**: 1-2日
**効果**: デプロイが1コマンドに

### Phase 2: VPC Endpoint & ECR の CFn化
**目標**: スクリプト00, 01をCFnに置き換え

**作業内容**:
1. `nested/network.yaml` 作成
   - VPC Endpoint for Bedrock AgentCore
   - Security Group設定
2. `nested/ecr.yaml` 作成
   - sila2-bridge リポジトリ（旧 bridge_container）
   - sila2-mock-devices リポジトリ（旧 mock_devices）
3. `main.yaml` に追加
4. スクリプト00, 01を削除

**注意**: ECRリポジトリ名は変更されていますが、イメージ参照は新しい名前を使用します。

**削減スクリプト**: 2つ（00, 01）
**期間**: 半日
**効果**: スクリプト7個 → 5個

### Phase 3: Lambda統合
**目標**: スクリプト05の一部をCFnに置き換え

**作業内容**:
1. `nested/lambda.yaml` に追加
   - analyze-heating-rate Lambda（src/lambda/tools/から）
   - Lambda Layer管理
2. S3バケットからコードデプロイ（src/lambda/配下のzipファイル）
3. スクリプト05を簡略化（Targetのみ残す）

**パス参照**: Lambda関数コードは `src/lambda/` 配下から取得します。

**削減スクリプト**: 0.5個（05の一部）
**期間**: 半日
**効果**: スクリプト5個 → 4.5個

### Phase 4: Custom Resource（Gateway/Target）
**目標**: スクリプト04, 05をCFnに置き換え

**作業内容**:
1. Custom Resource Lambda作成
   - Gateway管理
   - Target管理
2. `nested/agentcore.yaml` 作成
3. スクリプト04, 05を削除

**削減スクリプト**: 1.5個（04 + 05の残り）
**期間**: 1-2日
**効果**: スクリプト4.5個 → 3個

### Phase 5: AgentCore Runtime（保留）
**目標**: 現状維持

**理由**:
- agentcore CLIの複雑性
- CodeBuildプロジェクトの動的生成
- Dockerイメージビルド
- 費用対効果が低い

**結論**: スクリプト06は**そのまま残す**

## 最終的なスクリプト構成

### 01_build_containers.sh（必須）
```bash
#!/bin/bash
source scripts/utils/config.sh
source scripts/utils/common.sh

# Proto compile
compile_proto

# ECR login
ecr_login

# Build & Push（新フォルダ構成対応）
build_and_push_image "src/bridge" "$ECR_BRIDGE"
build_and_push_image "src/devices" "$ECR_MOCK"
```

### 02_package_lambdas.sh（必須）
```bash
#!/bin/bash
source scripts/utils/config.sh

# Package Lambda functions（新フォルダ構成対応）
package_lambda "src/lambda/proxy" "$DEPLOYMENT_BUCKET"
package_lambda "src/lambda/invoker" "$DEPLOYMENT_BUCKET"
package_lambda "src/lambda/tools/analyze_heating_rate" "$DEPLOYMENT_BUCKET"

# Create Lambda Layers
create_layer "requests" "$DEPLOYMENT_BUCKET"
create_layer "agentcore-dependencies" "$DEPLOYMENT_BUCKET"
```

### 03_deploy_stack.sh（必須）
```bash
#!/bin/bash
source scripts/utils/config.sh

# Package nested templates
aws cloudformation package \
  --template-file infrastructure/main.yaml \
  --s3-bucket "$DEPLOYMENT_BUCKET" \
  --output-template-file /tmp/packaged.yaml

# Deploy
aws cloudformation deploy \
  --template-file /tmp/packaged.yaml \
  --stack-name "$MAIN_STACK_NAME" \
  --parameter-overrides \
    VpcId="$VPC_ID" \
    PrivateSubnetIds="$PRIVATE_SUBNETS" \
    DeploymentBucket="$DEPLOYMENT_BUCKET" \
  --capabilities CAPABILITY_IAM
```

### 04_deploy_agentcore.sh（必須）
```bash
#!/bin/bash
# 現状のスクリプト06とほぼ同じ
# Gateway情報をCFn Outputから取得
source scripts/utils/config.sh

GATEWAY_ARN=$(get_stack_output "$MAIN_STACK_NAME" "GatewayArn")
GATEWAY_URL=$(get_stack_output "$MAIN_STACK_NAME" "GatewayUrl")

# agentcore configure & deploy
agentcore configure ...
agentcore deploy
```

## 共通関数（scripts/utils/）

### config.sh
```bash
# AWS設定
DEFAULT_REGION="${AWS_REGION:-us-west-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# スタック名
MAIN_STACK_NAME="sila2-main-stack"

# S3バケット（Lambda/CFnテンプレート用）
DEPLOYMENT_BUCKET="sila2-deployment-${ACCOUNT_ID}-${DEFAULT_REGION}"

# ECRリポジトリ
ECR_BRIDGE="sila2-bridge"
ECR_MOCK="sila2-mock-devices"
```

### common.sh（拡張）
```bash
# CloudFormation操作
get_stack_output() {
  aws cloudformation describe-stacks \
    --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" \
    --output text
}

# ECR操作
ecr_login() {
  aws ecr get-login-password --region "$DEFAULT_REGION" | \
    docker login --username AWS --password-stdin \
    "$ACCOUNT_ID.dkr.ecr.$DEFAULT_REGION.amazonaws.com"
}

# Docker操作（新フォルダ構成対応）
build_and_push_image() {
  local dir=$1
  local repo=$2
  local original_dir=$(pwd)
  cd "$dir"
  docker build -t "$repo:latest" .
  docker tag "$repo:latest" "$ACCOUNT_ID.dkr.ecr.$DEFAULT_REGION.amazonaws.com/$repo:latest"
  docker push "$ACCOUNT_ID.dkr.ecr.$DEFAULT_REGION.amazonaws.com/$repo:latest"
  cd "$original_dir"
}

# Lambda操作（新フォルダ構成対応）
package_lambda() {
  local dir=$1
  local bucket=$2
  local original_dir=$(pwd)
  cd "$dir"
  local zip_name=$(basename "$dir").zip
  zip -r "/tmp/$zip_name" . -x "*.pyc" "__pycache__/*"
  aws s3 cp "/tmp/$zip_name" "s3://$bucket/lambda/"
  cd "$original_dir"
}
```

## 実装順序（推奨）

### Week 1: CloudFormation基盤
1. **Day 1-2**: Phase 1（CFn統合）
2. **Day 3**: Phase 2（VPC/ECR）
3. **Day 4**: テスト・調整

### Week 2: 高度な統合
4. **Day 5**: Phase 3（Lambda統合）
5. **Day 6-7**: Phase 4（Custom Resource）
6. **Day 8**: 最終テスト

## 比較: スクリプト最適化 vs CFn統合

| 項目 | スクリプト最適化 | CFn統合（推奨） |
|------|-----------------|----------------|
| スクリプト数 | 7個（最適化） | 3個 |
| コード行数 | 665行 | 300行 |
| デプロイ時間 | 20-30分 | 15-20分 |
| ロールバック | 手動 | 自動 |
| 保守性 | 中 | 高 |
| 実装期間 | 3-4日 | 5-8日 |
| 長期メリット | 低 | 高 |

## 結論: CFn統合を推奨

### 理由
1. **スクリプト最適化は一時的**: 最終的にCFn化するなら無駄
2. **CFn統合は根本解決**: インフラをコード化
3. **長期的メリット**: ロールバック、再現性、保守性

### 推奨アプローチ
- **スクリプト最適化計画は破棄**
- **CloudFormation統合計画を実行**
- Phase 1-4を段階的に実施
- AgentCore（スクリプト06）のみ残す

## 実施順序（重要）

### ステップ1: フォルダ構成整理（必須・先行）
```bash
# FOLDER_STRUCTURE_PLAN.md を実施
# 所要時間: 2.5時間
```

### ステップ2: デプロイ最適化（この計画）
```bash
# Phase 1-4を順次実施
# 所要時間: 5-8日
```

## 次のステップ

1. ✅ FOLDER_STRUCTURE_PLAN.md を実施（必須）
2. ✅ この統合計画を承認
3. ⬜ Phase 1開始（CFnネストスタック作成）
