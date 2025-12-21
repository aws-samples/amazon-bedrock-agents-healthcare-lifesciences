# フォルダ掃除計画

**作成日**: 2025-01-31  
**対象**: `/agents_catalog/32-sila2-lab-automation-agent`  
**Phase**: Phase 5完了後のクリーンアップ

---

## 保持対象ファイル（削除しない）

### 📁 コアファイル
- `README.md` - メインドキュメント
- `main_agentcore_phase3.py` - Phase 5実装（現行版）
- `requirements.txt` - 依存関係
- `.bedrock_agentcore.yaml` - AgentCore設定
- `.gateway-config` - Gateway設定
- `.gitignore`
- `.dockerignore`
- `.python-version`

### 📁 フォルダ構造（全体保持）
- `scripts/` - デプロイスクリプト（01-06実績あり）
- `bridge_container/` - MCP Bridge実装
- `mock_devices/` - Mock Device実装
- `proto/` - Protobuf定義
- `lambda_proxy/` - Lambda Proxy実装
- `gateway/` - Gateway実装
- `tests/` - テストスクリプト
- `docs/` - ドキュメント
- `cloudformation/` - CloudFormation テンプレート

### 📁 Infrastructure（必要なもののみ）
- `infrastructure/bridge_container_ecs_no_alb.yaml` - ECS (scripts/03で使用)
- `infrastructure/lambda_proxy.yaml` - Lambda Proxy (scripts/03で使用)
- `infrastructure/device_api_gateway_enhanced.yaml` - API Gateway (scripts/01で使用)

### 📁 Gateway（scripts/01で参照）
- `gateway/agentcore_gateway_tools.py`
- `gateway/mcp_tool_registry.py`

### 📁 Lambda（scripts/01で参照）
- `device_discovery_lambda.py`

### 📁 テスト（scripts/01で参照）
- `test_phase3_integration.py`

### 📁 Streamlit UI
- `streamlit_mcp_tools.py` - 最新版（2024-12-17更新）

---

## 削除対象ファイル

### 🗑️ 1. 一時ファイル・ログ
```
streamlit_agentcore.log
streamlit.log
streamlit.pid
device_discovery.zip
mcp_grpc_bridge.zip
mock_centrifuge_device.zip
mock_hplc_device.zip
mock_pipette_device.zip
response.json
mcp_response.json
device_status.json
```

### 🗑️ 2. archiveフォルダ（全体）
```
archive/
```

### 🗑️ 3. Phase 3設定（Phase 5完了済み）
```
.phase3-config/
.phase3-complete-config
.phase3-step3-complete-config
.phase3-step5-complete-config
.phase3-step5-complete-with-agentcore-config
.bedrock_agentcore_backup.yaml
.bedrock_agentcore_simple.yaml
.device_api_config.json
```

### 🗑️ 4. 重複mainファイル
```
main.py
main_aws_official.py
main_aws_official_final.py
main_gateway.py
main_phase3.py
main_simple.py
main_strands_agentcore_phase3.py
main_agentcore_phase3_backup.py
app.py
```
**保持**: `main_agentcore_phase3.py` のみ

### 🗑️ 5. 重複Lambda実装
```
mcp_grpc_bridge_lambda_aws_format.py
mcp_grpc_bridge_lambda_fixed_v2.py
mcp_grpc_bridge_lambda_fixed.py
mcp_grpc_bridge_lambda_gateway.py
mcp_grpc_bridge_lambda_grpc.py
mcp_grpc_bridge_lambda_mcp_correct.py
mcp_grpc_bridge_lambda_mcp.py
mcp_grpc_bridge_lambda_v2.py
mcp_grpc_bridge_lambda_v3.py
protocol_bridge_lambda_grpc.py
protocol_bridge_lambda.py
```
**注**: `mcp_grpc_bridge_lambda_gateway.py`はREADME記載だが、scripts未使用のため削除候補

### 🗑️ 6. 重複Mock Device実装（ルート直下）
```
mock_centrifuge_device_lambda.py
mock_centrifuge_device_simple.py
mock_hplc_device_lambda.py
mock_hplc_device_simple.py
mock_pipette_device_lambda.py
mock_pipette_device_simple.py
simple_mock_device_lambda.py
grpc_mock_device_server.py
unified_mock_device_lambda.py
unified_mock_device_lambda_enhanced.py
```
**注**: `mock_devices/`フォルダに統合済み

### 🗑️ 7. 古いデプロイスクリプト（ルート直下）
```
deploy_phase3_architecture_complete.sh
deploy_phase3_complete.sh
deploy-agentcore-gateway.sh
deploy-phase3-complete-full-final.sh
deploy-phase3-complete-full-fixed.sh
deploy-phase3-complete-full.sh
deploy-phase3-complete.sh
deploy-phase3-final.sh
deploy-phase3-option-a.sh
deploy-phase3-step1-infra.sh
deploy-phase3-step1.sh
deploy-phase3-step2-code.sh
deploy-phase3-step2.sh
deploy-phase3-step3-full.sh
deploy-phase3-step3-test.sh
deploy-phase3-step3.sh
deploy-phase3-step4-agentcore.sh
deploy-phase3-step4-full.sh
deploy-phase3-step5-complete-with-agentcore.sh
deploy-phase3-step5-complete.sh
deploy-phase3-step5-runtime.sh
deploy-phase3.sh
fix-runtime-issue.sh
```
**注**: `scripts/`フォルダに整理済み

### 🗑️ 8. 重複requirements
```
requirements_backup.txt
requirements-phase3-minimal.txt
requirements_gateway.txt
requirements-minimal.txt
```
**保持**: `requirements.txt` のみ

### 🗑️ 9. 古いテストファイル（ルート直下）
```
test_phase3.py
test_phase5_agentcore.py
test_phase5_agentcore.sh
test_phase5_simple.py
test_agentcore_cli.py
test_agentcore_phase5.py
test_agentcore_runtime.py
test_agentcore_sdk.py
test_polling_agentcore_logs.py
test_polling_agentcore_simple.py
test_polling_agentcore.py
test_polling_detailed.py
test_polling_detailed.sh
test_polling_direct.py
test_polling_lambda.py
test_polling_lambda.sh
test_polling_manual.py
test_polling_streaming.py
test_polling.py
test_layers_fixed.py
test_layers.py
test_gateway_310.py
test_gateway.py
test_task_group_2.py
test_task_group_3.py
test_task_group_4.py
test_task_group_5.py
test_strands_integration.py
test-phase3-complete-full.sh
test-step1-deploy.sh
test-step2-deploy.sh
test-step3-complete.sh
test-step3-deploy.sh
test-step4-complete.sh
test-step5-integration.sh
test_streamlit_ui.sh
```
**注**: `tests/`フォルダに整理済み

### 🗑️ 10. 古いStreamlitファイル
```
streamlit_app_agentcore.py
streamlit_app_phase5.py
streamlit_app_agentcore_phase5.py
streamlit_phase3_test.py
streamlit_polling_demo.py
streamlit_polling_test.py
streamlit_polling.py
streamlit_direct_polling.py
streamlit_agentcore_polling_demo.py
streamlit_agentcore_polling.py
```
**保持**: `streamlit_mcp_tools.py` のみ（最新版）

### 🗑️ 11. 古いドキュメント（ルート直下 → docs/へ移動）
```
architecture.md
ARCHITECTURE_ROADMAP.md
LAMBDA_PROXY_SUCCESS_SUMMARY.md
MIGRATION_PLAN_MCP_GRPC.md
PHASE3_ARCHITECTURE_FIX_PLAN.md
PHASE3_DEVELOPMENT_PLAN.md
PHASE3_IMPROVEMENT_PLAN.md
PHASE5_COMPLETION_SUMMARY.md
PHASE5_IMPLEMENTATION_PLAN.md
POLLING_VISUALIZATION.md
README_POLLING_TEST.md
ROLLBACK_COMPLETED.md
SCRIPT_REORGANIZATION_SUMMARY.md
TASK1_COMPLETION_REPORT.md
TASK2_COMPLETION_REPORT.md
TASK7_COMPLETION_SUMMARY.md
TASK8_COMPLETION_SUMMARY.md
TASK15_COMPLETION_REPORT.md
TASK20_IMPLEMENTATION_SUMMARY.md
TASK_GROUP_6_COMPLETION_SUMMARY.md
```
**注**: これらは削除せず、`docs/archive/`へ移動する

### 🗑️ 12. 重複Infrastructure（ルート直下）
```
infrastructure/cfn-master.yaml
infrastructure/cfn-s3.yaml
infrastructure/cfn-sila2-agent-simple.yaml
infrastructure/cfn-sila2-agent.yaml
infrastructure/cfn-simple.yaml
infrastructure/cleanup.sh
infrastructure/deploy-agentcore.sh
infrastructure/deploy-iac.sh
infrastructure/deploy.sh
infrastructure/mock_device_api_gateway.yaml
infrastructure/sila2-agent-complete.yaml
infrastructure/sila2-agent-gateway.yaml
infrastructure/sila2-agent-infrastructure.yaml
infrastructure/sila2-agent-phase3-architecture.yaml
infrastructure/sila2-agent-simple-fixed.yaml
infrastructure/sila2-agent-simple.yaml
infrastructure/sila2-agentcore-gateway.yaml
infrastructure/sila2-minimal.yaml
infrastructure/sila2-phase3-agentcore-full.yaml
infrastructure/sila2-phase3-complete.yaml
infrastructure/sila2-phase3-enhanced.yaml
infrastructure/sila2-phase3-iam-fixed-v2.yaml
infrastructure/sila2-phase3-iam-fixed.yaml
infrastructure/sila2-phase3-iam-xray-fixed.yaml
infrastructure/sila2-phase3-step3.yaml
infrastructure/sila2-phase3-working.yaml
infrastructure/bridge_container_ecs.yaml
```
**保持**: 
- `bridge_container_ecs_no_alb.yaml`
- `lambda_proxy.yaml`
- `device_api_gateway_enhanced.yaml`

### 🗑️ 13. 重複Gateway実装（ルート直下）
```
gateway/agentcore_gateway_config.yaml
gateway/gateway_config.yaml
gateway/mock_device_lambda_enhanced.py
gateway/sila2_agentcore_gateway.py
gateway/sila2_client.py
gateway/sila2_devices_config.json
gateway/sila2_gateway_mcp_tools.py
gateway/sila2_gateway_tools_phase3.py
gateway/sila2_gateway_tools_simplified.py
gateway/sila2_gateway_tools.py
gateway/tool_schemas.json
gateway/unified_mock_device_lambda.py
```
**保持**:
- `agentcore_gateway_tools.py`
- `mcp_tool_registry.py`

### 🗑️ 14. その他重複ファイル
```
create_gateway_target.py
create_correct_gateway_target.py
fix_config.py
fix_gateway_config.py
fix-iam-policy.json
device_api_monitor.py
device_router.py
grpc_test_client.py
lambda_grpc_device_handler.py
sila2_client.py
sila2_devices_config.json
sila2_basic_pb2_grpc.py
sila2_basic_pb2.py
gateway_tools_impl.py
strands_polling_agent.py
performance_test.py
verify_architecture_compliance.sh
check_polling_logs.sh
run_streamlit.sh
agentcore_trust_policy.json
Dockerfile
Dockerfile.custom
```
**注**: `scripts/create_mcp_gateway_target.py`は保持（scripts/で使用）

### 🗑️ 15. MCP関連（ルート直下）
```
mcp/
```
**注**: `bridge_container/mcp_server.py`に統合済み

---

## 削除実行コマンド（確認後に実行）

```bash
# 一時ファイル
rm -f *.log *.pid *.zip response.json mcp_response.json device_status.json

# フォルダ
rm -rf archive/ .phase3-config/ mcp/

# 設定ファイル
rm -f .phase3-* .bedrock_agentcore_backup.yaml .bedrock_agentcore_simple.yaml .device_api_config.json

# mainファイル
rm -f main.py main_aws_official*.py main_gateway.py main_phase3.py main_simple.py main_strands_agentcore_phase3.py main_agentcore_phase3_backup.py app.py

# Lambdaファイル
rm -f mcp_grpc_bridge_lambda_*.py protocol_bridge_lambda*.py

# Mock Deviceファイル
rm -f mock_*_device_*.py simple_mock_device_lambda.py grpc_mock_device_server.py unified_mock_device_lambda*.py

# デプロイスクリプト
rm -f deploy*.sh fix-*.sh test-*.sh

# requirements
rm -f requirements_backup.txt requirements-phase3-minimal.txt requirements_gateway.txt requirements-minimal.txt

# テストファイル
rm -f test_*.py test_*.sh

# Streamlitファイル（最新版以外）
rm -f streamlit_app_agentcore.py streamlit_app_phase5.py streamlit_app_agentcore_phase5.py streamlit_phase3_test.py streamlit_polling*.py streamlit_direct_polling.py streamlit_agentcore_polling*.py

# ドキュメントをdocs/archive/へ移動
mkdir -p docs/archive
mv *.md docs/archive/ 2>/dev/null || true
mv README.md CLEANUP_PLAN.md . 2>/dev/null || true.py streamlit_polling*.py streamlit_direct_polling.py streamlit_agentcore_polling*.py streamlit_mcp_tools.py

# ドキュメント
rm -f PHASE*.md TASK*.md MIGRATION_*.md ROLLBACK_*.md LAMBDA_*.md POLLING_*.md README_POLLING_TEST.md SCRIPT_*.md ARCHITECTURE_ROADMAP.md architecture.md

# その他
rm -f create_gateway_target.py create_correct_gateway_target.py fix_*.py device_api_monitor.py device_router.py grpc_test_client.py lambda_grpc_device_handler.py sila2_client.py sila2_devices_config.json sila2_basic_pb2*.py gateway_tools_impl.py strands_polling_agent.py performance_test.py verify_architecture_compliance.sh check_polling_logs.sh run_streamlit.sh agentcore_trust_policy.json Dockerfile Dockerfile.custom
```

---

## 確認事項

- [ ] バックアップ作成済み
- [ ] scripts/01-06の動作確認済み
- [ ] README.mdの参照ファイル確認済み
- [ ] 削除対象に必要なファイルが含まれていないか確認
- [ ] 削除実行前に再度レビュー

---

**注意**: このファイルは削除計画です。実際の削除は慎重に行ってください。
