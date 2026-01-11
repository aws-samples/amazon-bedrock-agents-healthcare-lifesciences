# フォルダ整理計画

## 整理方針

1. **スクリプト00-06で参照されるファイルは保持**（デプロイに必須）
2. 削除せずに `_to_review/` ディレクトリに移動
3. 動作確認後、不要と判断したものを削除
4. 公開前に機密情報を完全に除外

## スクリプト00-06の依存関係（保持必須）

### 必須ディレクトリ・ファイル
```
scripts/
  utils/
    common.sh              # 全スクリプトで使用
    aws_helpers.sh
    validation.sh
  00_setup_vpc_endpoint.sh
  01_setup_infrastructure.sh
  02_build_containers.sh
  03_deploy_ecs.sh
  04_create_gateway.sh
  05_create_mcp_target.sh
  06_deploy_agentcore.sh

infrastructure/
  bridge_container_ecs_no_alb.yaml  # 03で使用
  lambda_proxy.yaml                  # 03で使用
  phase6-cfn.yaml                    # 03で使用

bridge_container/                    # 02でビルド
  proto/
  *.py
  Dockerfile
  requirements.txt

mock_devices/                        # 02でビルド
  proto/
  *.py
  Dockerfile
  requirements.txt

proto/                               # 02でコンパイル
  *.proto
  *_pb2.py
  *_pb2_grpc.py

lambda_proxy/                        # 03で更新
  index.py
  requirements.txt

lambda/invoker/                      # 03, 06で更新
  lambda_function.py
  requirements.txt

lambda/tools/analyze_heating_rate/   # 05で使用
  index.py

agentcore/                           # 06で使用
  agent_instructions.txt
  gateway_config.py
  runtime_config.py
  verify_setup.py

main_agentcore_phase3.py             # 06で使用
requirements.txt                     # 06で使用
.bedrock_agentcore.yaml              # 06で生成・更新
.gateway-config                      # 04, 05, 06で生成・参照
```

## 移動対象ファイル

### 1. ログファイル（_to_review/logs/）
```
streamlit_8502.log
streamlit.log
test_abort_result.log
test_analyze_result.log
```

### 2. ビルド成果物（_to_review/build/）
```
lambda_invoker.zip
lambda/invoker/lambda_function.zip
```

### 3. 機密情報（_to_review/secrets/）- 公開前に必ず削除
```
.env
.streamlit/secrets.toml
.gateway-config
```

### 4. バックアップ（_to_review/backup/）
```
scripts/phase6.backup/
docs/archive/
agentcore/agent_instructions.txt.backup
```

### 5. 一時ファイル（_to_review/temp/）
```
response.json
```

### 6. 開発フェーズドキュメント（_to_review/phase_docs/）- 統合版を残す
ルートディレクトリの以下のファイル：
```
PHASE5_ARCHITECTURE.md
PHASE5_IMPLEMENTATION.md
PHASE5_OVERVIEW.md
PHASE5_6_7_SCENARIO_SWITCHING.md
PHASE6_ARCHITECTURE.md
PHASE6_CHECKLIST.md
PHASE6_COMPLETE.md
PHASE6_DEPLOYMENT_COMPLETE.md
PHASE6_DEPLOYMENT_GUIDE.md
PHASE6_DEPLOYMENT_IMPLEMENTED.md
PHASE6_DEPLOYMENT_PLAN.md
PHASE6_DEPLOYMENT_REPORT.md
PHASE6_HANDOFF.md
PHASE6_IMPLEMENTATION.md
PHASE6_OVERVIEW.md
PHASE6_SCRIPT_UPDATE_SUMMARY.md
PHASE6_VPC_COMPLETE.md
PHASE7_AGENTCORE_GUIDE.md
PHASE7_ARCHITECTURE.md
PHASE7_CORRECTION_COMPLETE.md
PHASE7_CORRECTION_PLAN.md
PHASE7_DEPLOYMENT_PLAN.md
PHASE7_HEATING_STATUS_MODIFICATION_PLAN.md
PHASE7_IMPLEMENTATION.md
PHASE7_LAMBDA_INVOKER_UPDATE.md
PHASE7_LOCAL_TEST_COMPLETE.md
PHASE7_OVERVIEW.md
PHASE7_PHASE5_INTEGRATION.md
PHASE7_STEP0_COMPLETE.md
PHASE7_STEP1_COMPLETE.md
PHASE7_STEP2_COMPLETE.md
PHASE7_STEP3_COMPLETE.md
DEPLOYMENT_SCRIPTS_UPDATE_PLAN.md
DEPLOYMENT_STATUS.md
DEMO_OPTIMIZATION_PLAN.md
EVENT_FLOW_GUIDE.md
HANDOVER_NOTES.md
TEST_RESULTS.md
STREAMLIT_ACCESS.md
```

### 7. 重複Streamlitアプリ（_to_review/streamlit_versions/）
```
streamlit_app/phase6_monitor_lambda.py
streamlit_app/phase6_monitor.py
streamlit_app/phase7_app.py
streamlit_app/phase7_demo.py
streamlit_app/phase7_final_fixed.py
streamlit_app/phase7_fixed.py
streamlit_app/demo_ui.py
streamlit_app/monitoring_ui.py
streamlit_app/simple_demo.py
streamlit_app/ai_analysis.py
streamlit_app/create_test_event.py
streamlit_app/proto/  # UI用protoファイル
```
→ **phase7_final.py のみ残す**

### 8. 重複起動スクリプト（_to_review/run_scripts/）
```
run_phase6_ui.sh
run_phase7_ui.sh
run_streamlit.sh
start_ui_lambda.sh
start_ui.sh
streamlit_app/run_demo.sh
streamlit_app/run_final.sh
streamlit_app/run_phase7_app.sh
streamlit_app/run_phase7_demo.sh
streamlit_app/run_simple_demo.sh
```
→ 統合版1つに集約

### 9. 未使用テストスクリプト（_to_review/test_scripts/）
```
scripts/test_*.sh                        # 全て未使用
scripts/verify_*.sh                      # 全て未使用
test_heating_rate_tool.sh                # 未使用
```
→ 必要に応じて tests/ ディレクトリに統合版を作成

### 10. 重複Pythonテストファイル（_to_review/python_tests/）
```
test_agentcore_invoke.py
test_phase3_integration.py
test_phase4_integration.py
test_phase7_tools.py
streamlit_app/test_memory.py
streamlit_app/test_rerun.py
streamlit_app/test_session.py
lambda/invoker/test_memory_boto3.py
lambda/invoker/test_memory_correct.py
lambda/invoker/test_memory.py
```
→ tests/ ディレクトリに統合

### 11. 重複protoファイル（保持 - ビルドに必要）
以下のディレクトリに同じprotoファイルが存在：
```
proto/                    # ソース（保持）
bridge_container/proto/   # 02でコピー（保持）
mock_devices/proto/       # 02でコピー（保持）
streamlit_app/proto/      # UI用（移動可能）
```
→ proto/, bridge_container/proto/, mock_devices/proto/ は**保持必須**
→ streamlit_app/proto/ のみ _to_review/streamlit_versions/ に移動可能

### 12. 未使用デプロイスクリプト（_to_review/deploy_scripts/）
```
scripts/deploy_all.sh                    # 00-06に統合済み
scripts/deploy-phase6.sh                 # 03に統合済み
scripts/deploy-phase7-step1.sh           # 未使用
scripts/deploy-phase7-step2-agentcore.sh # 06に統合済み
scripts/integration_test.sh              # 未使用
scripts/run-local-test.sh                # 未使用
scripts/05b_update_gateway_targets.sh    # 未使用
scripts/06_deploy_lambda_with_layer.sh   # 03に統合済み
scripts/07_run_tests.sh                  # 未使用
scripts/08_setup_ui.sh                   # 未使用
scripts/08_test_phase7_integration.sh    # 未使用
scripts/09_cleanup_nlb.sh                # 未使用
```

### 13. 一時ヘルパースクリプト（_to_review/helper_scripts/）
```
associate_memory_fixed.sh
associate_memory.sh
check_connection.sh
delete_memory_event.py
device_discovery_lambda.py
fix_iam_permissions.sh
start_grpc_forward.sh
start_port_forward_ecs.sh
start_port_forward.sh
update_lambda_env.sh
scripts/add_memory_strategy.py
scripts/check_current_status.sh
scripts/cleanup_duplicate_memories.sh
scripts/create_mcp_gateway_target.py
scripts/delete_lambda_gateway_target.py
scripts/monitor_event_flow.sh
```
→ 必要なものは scripts/utils/ に統合

## 残すべきファイル（公開用）

### デプロイに必須（スクリプト00-06で使用）
```
scripts/
  utils/
  00_setup_vpc_endpoint.sh
  01_setup_infrastructure.sh
  02_build_containers.sh
  03_deploy_ecs.sh
  04_create_gateway.sh
  05_create_mcp_target.sh
  06_deploy_agentcore.sh

infrastructure/
  bridge_container_ecs_no_alb.yaml
  lambda_proxy.yaml
  phase6-cfn.yaml

bridge_container/
mock_devices/
proto/
lambda_proxy/
lambda/invoker/
lambda/tools/analyze_heating_rate/
agentcore/
main_agentcore_phase3.py
requirements.txt
```

### ドキュメント
- README.md (作成予定)
- CLEANUP_PLAN.md (このファイル - 整理計画)
- DEPLOYMENT_OPTIMIZATION_PLAN.md (デプロイ最適化計画)
- docs/ARCHITECTURE.md (統合版作成予定)
- docs/DEPLOYMENT.md (統合版作成予定)

### 設定ファイル
- .gitignore
- .dockerignore
- docker-compose.yml

### オプション（UI）
```
streamlit_app/
  phase7_final.py        # メインアプリ
  requirements.txt
  Dockerfile
  README*.md
  QUICKSTART.md
  run_final.sh           # 起動スクリプト
```

## 実行手順

1. バックアップ作成
2. _to_review/ ディレクトリに移動
3. デプロイ・テスト実行で動作確認
4. 問題なければ _to_review/ を削除
5. 機密情報の完全削除確認

## 注意事項

- 機密情報（.env, secrets.toml等）は公開前に必ず削除
- protoファイルの統合は依存関係を確認してから実施
- スクリプト統合は段階的に実施し、各段階で動作確認


## 追加で移動・削除すべきファイル（レビュー後発見）

### 14. ビルド成果物（追加）⚠️ 移動必要
```
lambda/lambda_invoker.zip  # ルートlambdaディレクトリに残存
```
→ _to_review/build/ に移動

### 15. Lambda Layer（削除推奨）⚠️ 新規追加
```
lambda/invoker/layer/python/  # 巨大なboto3/botocore依存関係
```
→ **03_deploy_ecs.shで自動生成されるため、リポジトリに含める必要なし**
→ .gitignoreに追加して除外

### 16. 開発用キャッシュ（削除推奨）⚠️ 新規追加
```
.pytest_cache/
.venv/
```
→ .gitignoreに追加して除外

### 17. 重複README（追加）⚠️ 移動必要
```
streamlit_app/README_DEMO.md
streamlit_app/README_PHASE7.md
streamlit_app/README_PHASE7_UI.md
```
→ _to_review/streamlit_versions/ に移動
→ streamlit_app/README.md を新規作成（統合版）

## 更新された実行手順

### フェーズ1: 残存ファイルの移動
1. `lambda/lambda_invoker.zip` を `_to_review/build/` に移動
2. `streamlit_app/README_*.md` を `_to_review/streamlit_versions/` に移動
3. `streamlit_app/README.md` を新規作成（統合版）

### フェーズ2: 不要ファイルの削除
1. `lambda/invoker/layer/` を削除（.gitignoreに追加）
2. `.pytest_cache/` を削除（.gitignoreに追加）
3. `.venv/` を削除（.gitignoreに追加）

### フェーズ3: 動作確認
1. デプロイスクリプト00-06を順次実行
2. 各ステップで動作確認
3. 問題なければ次のフェーズへ

### フェーズ4: 最終クリーンアップ
1. `_to_review/` ディレクトリ全体を削除
2. 機密情報（.env, secrets.toml等）の完全削除確認
3. .gitignoreの更新確認

## 進捗状況

✅ 完了: 1-13の移動作業（既に_to_review/に移動済み）

⚠️ 残作業:
  - lambda/lambda_invoker.zip の移動
  - streamlit_app/README_*.md の移動と統合
  - lambda/invoker/layer/ の削除と.gitignore追加
  - .pytest_cache/, .venv/ の削除と.gitignore追加

## .gitignoreに追加すべきエントリ

```
# Lambda Layer (自動生成)
lambda/invoker/layer/

# Python環境
.venv/
venv/
.pytest_cache/

# ビルド成果物
*.zip
lambda_invoker.zip
lambda_function.zip

# 機密情報
.env
.gateway-config
.streamlit/secrets.toml
```
