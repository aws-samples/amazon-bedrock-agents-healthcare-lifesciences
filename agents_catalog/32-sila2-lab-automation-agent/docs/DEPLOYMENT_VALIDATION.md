# Deployment Validation Report

**Date**: 2025-01-28  
**Region**: us-west-2  
**Status**: ✅ Fixed - ECR Only Approach

---

## Issue Summary

クリーンアップ後の初回デプロイで、スクリプトが古いPhase 3アーキテクチャを参照し、CloudFormationがコンテナイメージ不在でエラーになった。

---

## Root Cause Analysis

### 1. Architecture Mismatch

| Component | Phase 3 (Backup) | Phase 4 (Current) |
|-----------|------------------|-------------------|
| Compute | Lambda | ECS Fargate |
| Bridge | Lambda Function | Container |
| Mock Devices | 3 Lambda Functions | 1 Container |
| Deployment | CloudFormation (Lambda) | CloudFormation (ECS) |

### 2. Deployment Order Issue

**誤った順序** (最初の試み):
```
01: ECR + CloudFormation → ❌ イメージ不在エラー
```

**正しい順序**:
```
01: ECR作成
02: コンテナビルド＆プッシュ
03: CloudFormation（ECS）デプロイ
```

### 3. Actual Error

```
CannotPullContainerError: pull image manifest has been retried 7 time(s): 
failed to resolve ref 590183741681.dkr.ecr.us-west-2.amazonaws.com/sila2-bridge:latest: 
not found
```

**原因**: CloudFormationがECSタスクを起動しようとしたが、コンテナイメージが存在しない

---

## Applied Fix

### `scripts/01_setup_infrastructure.sh`

**変更前** (Phase 3):
- Phase 3アーキテクチャ検証
- Lambda パッケージ作成
- CloudFormation デプロイ
- IAM設定
- 統合テスト

**変更後** (Phase 4):
- ECR リポジトリ作成のみ
  - `sila2-bridge`
  - `sila2-mock-devices`

**削除した処理**:
1. `verify_phase3_architecture()` - Phase 3検証
2. `deploy_agentcore_runtime()` - Strands検証
3. `deploy_cloudformation()` - CloudFormationデプロイ（03に移動）
4. `create_lambda_package()` - Lambda作成（不要）
5. `setup_iam_permissions()` - IAM設定（03に含まれる）
6. `update_lambda_functions()` - Lambda更新（不要）
7. `run_integration_tests()` - テスト（07に移動）

**最終実装**:
```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

main() {
    log_info "=== Step 01: Infrastructure Setup ==="
    
    if ! cd "$(dirname "$SCRIPT_DIR")"; then
        log_error "Failed to change to project directory"
        exit 1
    fi
    
    log_info "Creating ECR repositories..."
    aws ecr describe-repositories --repository-names sila2-bridge --region "$AWS_REGION" 2>/dev/null || \
      aws ecr create-repository --repository-name sila2-bridge --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true
    
    aws ecr describe-repositories --repository-names sila2-mock-devices --region "$AWS_REGION" 2>/dev/null || \
      aws ecr create-repository --repository-name sila2-mock-devices --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true
    
    log_info "✅ Step 01 complete - ECR repositories created"
    log_info "Next: ./scripts/02_build_containers.sh"
}

main "$@"
```

---

## Validation

### Script Consistency Check

| Script | Purpose | ECR Creation | Container Build | CloudFormation |
|--------|---------|--------------|-----------------|----------------|
| 01 | Infrastructure | ✅ | - | - |
| 02 | Build | ✅ (冪等) | ✅ | - |
| 03 | Deploy | - | - | ✅ |

✅ **整合性確認**: 
- 01でECR作成
- 02でECR作成も含む（冪等性あり）
- 03でCloudFormation（VPC自動取得）

---

## Deployment Steps

```bash
# Step 01: ECR作成
export AWS_REGION=us-west-2
./scripts/01_setup_infrastructure.sh

# Step 02: コンテナビルド
./scripts/02_build_containers.sh

# Step 03: ECSデプロイ
./scripts/03_deploy_ecs.sh

# Step 04-09: 残りのステップ
./scripts/04_create_gateway.sh
./scripts/05_create_mcp_target.sh
./scripts/06_deploy_agentcore.sh
./scripts/07_run_tests.sh
./scripts/08_setup_ui.sh
```

---

## Lessons Learned

1. **Architecture Evolution**: Phase 3→4移行時はスクリプト全体の見直しが必要
2. **Deployment Order**: コンテナベースはイメージ作成→デプロイの順序が必須
3. **Idempotency**: 02がECR作成を含むことで、01スキップも可能
4. **Error Messages**: CloudFormationエラーは根本原因（イメージ不在）を示す
5. **Backup Reference**: バックアップから元の意図を確認することが重要

---

## Status

- [x] 01スクリプト修正完了
- [x] Phase 3→Phase 4移行完了
- [x] デプロイ順序確認
- [ ] 実デプロイテスト待ち

**Next Action**: Step 01から順次実行
