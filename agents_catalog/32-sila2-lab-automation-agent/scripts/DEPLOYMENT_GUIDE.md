# デプロイ手順

## 概要

このエージェントは2段階デプロイが必要です：
1. **Phase 1**: ECRリポジトリ作成 + コンテナイメージプッシュ
2. **Phase 2**: 全リソースデプロイ（ECS/Lambda/AgentCore）

## 前提条件

- AWS CLI設定済み
- Docker実行環境
- VPC ID と プライベートサブネット2つ（異なるAZ）

## デプロイ手順

### Phase 1: ECRとコンテナイメージ

```bash
# 1. ECRリポジトリのみ作成
./scripts/01_deploy_ecr.sh

# 2. コンテナビルド & プッシュ
./scripts/02_build_containers.sh

# 3. Lambdaパッケージ
./scripts/03_package_lambdas.sh
```

### Phase 2: 全リソースデプロイ

```bash
# 4. メインスタックデプロイ
./scripts/04_deploy_stack.sh --vpc-id vpc-xxxxx --subnet-ids subnet-xxxxx,subnet-yyyyy

# 5. AgentCore Runtimeデプロイ
./scripts/05_deploy_agentcore.sh
```

## スクリプト説明

| スクリプト | 目的 | 所要時間 |
|-----------|------|---------|
| 01_deploy_ecr.sh | ECRリポジトリ作成（CFn） | 1-2分 |
| 02_build_containers.sh | Dockerビルド & ECRプッシュ | 5-10分 |
| 03_package_lambdas.sh | Lambda関数パッケージ | 1-2分 |
| 04_deploy_stack.sh | メインスタック（ECS/Lambda/Gateway） | 15-20分 |
| 05_deploy_agentcore.sh | AgentCore Runtime | 5-10分 |

## クリーンアップ

```bash
# AgentCore削除
agentcore delete

# CloudFormationスタック削除
aws cloudformation delete-stack --stack-name sila2-main-stack
aws cloudformation delete-stack --stack-name sila2-ecr-stack

# ECRイメージ削除
aws ecr batch-delete-image --repository-name sila2-bridge --image-ids imageTag=latest
aws ecr batch-delete-image --repository-name sila2-mock-devices --image-ids imageTag=latest
```
