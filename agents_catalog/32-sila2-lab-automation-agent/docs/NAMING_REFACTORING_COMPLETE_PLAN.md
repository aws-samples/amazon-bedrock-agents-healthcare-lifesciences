# 命名修正計画（完全版）

## 修正されるもの

### ✅ ローカルファイル名（7個）
- `main_agentcore_phase3.py` → `main_agentcore.py`
- `.bedrock_agentcore/sila2_phase3_agent/` → `.bedrock_agentcore/sila2_agent/`
- `infrastructure/phase6-cfn.yaml` → `infrastructure/events_sns.yaml`
- `scripts/test-phase6.sh` → `scripts/test_events.sh`
- `streamlit_app/phase7_final.py` → `streamlit_app/app.py`
- `test_phase4_integration.py` → `test_integration.py`
- `docs/architecture_phase4.md` → `docs/architecture.md`

### ✅ デプロイされるAWSリソース名

#### Lambda関数
```python
# 現在
phase7-analyze_heating_rate
phase7-execute_autonomous_control

# 変更後
sila2-analyze-heating-rate
sila2-execute-autonomous-control
```

#### AgentCore Runtime
```yaml
# 現在
runtime_name: sila2_phase3_agent
ecr_repository: bedrock-agentcore-sila2_phase3_agent
memory_name: sila2_phase7_memory

# 変更後
runtime_name: sila2_agent
ecr_repository: bedrock-agentcore-sila2_agent
memory_name: sila2_memory
```

#### CloudFormation Stack
```bash
# 現在
sila2-phase6-stack

# 変更後
sila2-events-stack
```

## 実行手順

### Step 1: ファイル名変更
```bash
cd /home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent

# メインファイル
git mv main_agentcore_phase3.py main_agentcore.py
git mv .bedrock_agentcore/sila2_phase3_agent .bedrock_agentcore/sila2_agent

# インフラ・スクリプト
git mv infrastructure/phase6-cfn.yaml infrastructure/events_sns.yaml
git mv scripts/test-phase6.sh scripts/test_events.sh

# Streamlit
git mv streamlit_app/phase7_final.py streamlit_app/app.py

# テスト・ドキュメント
git mv test_phase4_integration.py test_integration.py
git mv docs/architecture_phase4.md docs/architecture.md
```

### Step 2: Lambda関数名変更
```bash
# agentcore/gateway_config.py
sed -i 's/phase7-analyze_heating_rate/sila2-analyze-heating-rate/g' agentcore/gateway_config.py
sed -i 's/phase7-execute_autonomous_control/sila2-execute-autonomous-control/g' agentcore/gateway_config.py

# agentcore/verify_setup.py
sed -i 's/phase7-analyze_heating_rate/sila2-analyze-heating-rate/g' agentcore/verify_setup.py
sed -i 's/phase7-execute_autonomous_control/sila2-execute-autonomous-control/g' agentcore/verify_setup.py
```

### Step 3: AgentCore設定変更
```bash
# .bedrock_agentcore.yaml
sed -i 's/sila2_phase3_agent/sila2_agent/g' .bedrock_agentcore.yaml
sed -i 's/main_agentcore_phase3\.py/main_agentcore.py/g' .bedrock_agentcore.yaml
sed -i 's/sila2_phase7_memory/sila2_memory/g' .bedrock_agentcore.yaml
```

### Step 4: スクリプト内の参照を更新
```bash
# scripts/00_setup_vpc_endpoint.sh
sed -i 's/sila2-phase6-stack/sila2-events-stack/g' scripts/00_setup_vpc_endpoint.sh

# scripts/03_deploy_ecs.sh
sed -i 's/phase6-cfn\.yaml/events_sns.yaml/g' scripts/03_deploy_ecs.sh
sed -i 's/sila2-phase6-stack/sila2-events-stack/g' scripts/03_deploy_ecs.sh
sed -i 's/phase6-lambda\.zip/events-lambda.zip/g' scripts/03_deploy_ecs.sh

# scripts/06_deploy_agentcore.sh
sed -i 's/sila2_phase3_agent/sila2_agent/g' scripts/06_deploy_agentcore.sh
sed -i 's/main_agentcore_phase3\.py/main_agentcore.py/g' scripts/06_deploy_agentcore.sh
sed -i 's/sila2_phase7_memory/sila2_memory/g' scripts/06_deploy_agentcore.sh
sed -i 's/sila2-phase6-stack-LambdaExecutionRole/sila2-events-stack-LambdaExecutionRole/g' scripts/06_deploy_agentcore.sh

# scripts/07_run_tests.sh
sed -i 's/test_phase4_integration\.py/test_integration.py/g' scripts/07_run_tests.sh
```

### Step 5: ドキュメント更新
```bash
# README.md
sed -i 's/phase7_app\.py/app.py/g' README.md
sed -i 's/phase7_final\.py/app.py/g' README.md
sed -i 's/phase6-invoker/sila2-agentcore-invoker/g' README.md

# streamlit_app/QUICKSTART.md
sed -i 's/phase7_final\.py/app.py/g' streamlit_app/QUICKSTART.md

# streamlit_app/app.py
sed -i 's/Phase 7 Final Implementation/SiLA2 Lab Automation Streamlit UI/g' streamlit_app/app.py

# scripts/test_events.sh
sed -i 's/Testing Phase 6 deployment/Testing SNS and EventBridge integration/g' scripts/test_events.sh

# infrastructure/events_sns.yaml
sed -i 's/Phase 6 - EventBridge/EventBridge/g' infrastructure/events_sns.yaml
sed -i 's/Security group for Phase 6 Lambda function/Security group for Lambda function/g' infrastructure/events_sns.yaml

# infrastructure/eventbridge-scheduler.yaml (deprecated file)
sed -i 's/phase6-cfn\.yaml/events_sns.yaml/g' infrastructure/eventbridge-scheduler.yaml

# scripts/README.md
sed -i 's/08_integrate_phase3\.sh/08_integrate_agentcore.sh/g' scripts/README.md

# REQUIRED_FILES.md
sed -i 's/main_agentcore_phase3\.py/main_agentcore.py/g' REQUIRED_FILES.md
sed -i 's/streamlit_app\/phase7_final\.py/streamlit_app\/app.py/g' REQUIRED_FILES.md
```

### Step 6: 検証
```bash
# "phase"残存確認（ドキュメントファイル除く）
grep -r "phase" --include="*.py" --include="*.yaml" --include="*.sh" . \
  --exclude-dir=".git" \
  | grep -v "PLAN.md" \
  | grep -v "CLEANUP_PLAN.md" \
  | grep -v "docs/" \
  | grep -v "eventbridge-scheduler.yaml"

# 構文チェック
python -m py_compile main_agentcore.py
python -m py_compile agentcore/gateway_config.py
python -m py_compile streamlit_app/app.py
python -m py_compile test_integration.py

# CloudFormationテンプレート検証
aws cloudformation validate-template --template-body file://infrastructure/events_sns.yaml
```

## デプロイ後のリソース名

### Lambda関数
- ✅ `sila2-agentcore-invoker`
- ✅ `sila2-analyze-heating-rate`
- ✅ `sila2-execute-autonomous-control`

### AgentCore
- ✅ Runtime: `sila2_agent`
- ✅ ECR: `bedrock-agentcore-sila2_agent`
- ✅ Memory: `sila2_memory`

### CloudFormation Stack
- ✅ Stack: `sila2-events-stack` (旧: sila2-phase6-stack)

### SNS/EventBridge
- ✅ Topic: `sila2-events-topic`
- ✅ Rule: `sila2-periodic-data-collection`

## チェックリスト

### 実行前
- [ ] Gitブランチ作成
- [ ] 現在のディレクトリ確認

### 変更作業
- [ ] Step 1: ファイル名変更（7個）
- [ ] Step 2: Lambda関数名変更
- [ ] Step 3: AgentCore設定変更
- [ ] Step 4: スクリプト内の参照を更新
- [ ] Step 5: ドキュメント更新

### 検証
- [ ] "phase"残存確認
- [ ] 構文チェック実行
- [ ] CloudFormationテンプレート検証

## 所要時間

- Step 1-5: 30分
- Step 6: 15分
- **合計: 45分**

## 注意事項

1. **新規デプロイ**: 全リソースが新しい名前で作成される
2. **Git履歴**: `git mv` でファイル履歴を保持
3. **docs/**: アーキテクチャドキュメントは参考資料として残す
4. **eventbridge-scheduler.yaml**: 非推奨ファイルだが参照を更新

## 修正箇所サマリー

### scripts/00_setup_vpc_endpoint.sh
- `sila2-phase6-stack` → `sila2-events-stack` (1箇所)

### scripts/03_deploy_ecs.sh
- `phase6-cfn.yaml` → `events_sns.yaml` (2箇所)
- `sila2-phase6-stack` → `sila2-events-stack` (3箇所)
- `phase6-lambda.zip` → `events-lambda.zip` (2箇所)

### scripts/06_deploy_agentcore.sh
- `sila2_phase3_agent` → `sila2_agent` (26箇所)
- `main_agentcore_phase3.py` → `main_agentcore.py` (4箇所)
- `sila2_phase7_memory` → `sila2_memory` (3箇所)
- `sila2-phase6-stack-LambdaExecutionRole` → `sila2-events-stack-LambdaExecutionRole` (1箇所)

### infrastructure/eventbridge-scheduler.yaml
- `phase6-cfn.yaml` → `events_sns.yaml` (2箇所)

### infrastructure/events_sns.yaml (phase6-cfn.yaml)
- Description: `Phase 6 - EventBridge` → `EventBridge` (1箇所)
- GroupDescription: `Security group for Phase 6 Lambda function` → `Security group for Lambda function` (1箇所)

### scripts/07_run_tests.sh
- `test_phase4_integration.py` → `test_integration.py` (1箇所)

### scripts/README.md
- `08_integrate_phase3.sh` → `08_integrate_agentcore.sh` (1箇所)

### REQUIRED_FILES.md
- `main_agentcore_phase3.py` → `main_agentcore.py` (1箇所)
- `streamlit_app/phase7_final.py` → `streamlit_app/app.py` (1箇所)
