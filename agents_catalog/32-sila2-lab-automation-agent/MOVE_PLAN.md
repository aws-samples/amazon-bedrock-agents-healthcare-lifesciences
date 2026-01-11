# 追加移動計画

## 現状確認
- ✅ 既に_to_review/に移動済み: phase_docs, streamlit_versions, test_scripts, python_tests, deploy_scripts, helper_scripts, backup, logs, temp, secrets, build(一部)

## 追加で_to_review/に移動すべきファイル・ディレクトリ

### 1. ビルド成果物 → _to_review/build/
```
lambda/lambda_invoker.zip
lambda/invoker/layer/
```

### 2. 開発用キャッシュ → _to_review/cache/
```
.pytest_cache/
.venv/
venv/
.python-version
__pycache__/
```

### 3. 重複README → _to_review/streamlit_versions/
```
streamlit_app/README_DEMO.md
streamlit_app/README_PHASE7.md
streamlit_app/README_PHASE7_UI.md
```

### 4. 生成ディレクトリ → _to_review/generated/
```
.bedrock_agentcore/
build/
```

### 5. 未使用ディレクトリ → _to_review/unused/
```
cloudformation/  # 内容確認必要
gateway/         # 内容確認必要
docs/            # 内容確認必要
tests/           # 内容確認必要
```

### 6. 開発用ファイル → _to_review/dev_files/
```
.env.phase6.template
docker-compose.yml
Dockerfile  # ルートのDockerfile（streamlit_app/Dockerfileは残す）
streamlit_mcp_tools.py
```

### 7. GitHub設定 → _to_review/github/
```
.github/
```

## 移動後に残るファイル・ディレクトリ（必須のみ）

```
.dockerignore
.gitignore
CLEANUP_PLAN.md
DEPLOYMENT_OPTIMIZATION_PLAN.md
README.md
REQUIRED_FILES.md
main_agentcore_phase3.py
requirements.txt

agentcore/
bridge_container/
infrastructure/
lambda/
  invoker/
    lambda_function.py
    requirements.txt
  tools/
    analyze_heating_rate/
      index.py
      requirements.txt
lambda_proxy/
mock_devices/
proto/
scripts/
  utils/
  00_setup_vpc_endpoint.sh
  01_setup_infrastructure.sh
  02_build_containers.sh
  03_deploy_ecs.sh
  04_create_gateway.sh
  05_create_mcp_target.sh
  06_deploy_agentcore.sh
streamlit_app/
  phase7_final.py
  requirements.txt
  Dockerfile
  QUICKSTART.md

_to_review/  # 全ての移動済みファイル
```

## 実行コマンド（まだ実行しない）

```bash
# 1. ビルド成果物
mv lambda/lambda_invoker.zip _to_review/build/ 2>/dev/null || true
mv lambda/invoker/layer _to_review/build/ 2>/dev/null || true

# 2. 開発用キャッシュ
mkdir -p _to_review/cache
mv .pytest_cache _to_review/cache/ 2>/dev/null || true
mv .venv _to_review/cache/ 2>/dev/null || true
mv venv _to_review/cache/ 2>/dev/null || true
mv .python-version _to_review/cache/ 2>/dev/null || true
mv __pycache__ _to_review/cache/ 2>/dev/null || true

# 3. 重複README
mv streamlit_app/README_DEMO.md _to_review/streamlit_versions/ 2>/dev/null || true
mv streamlit_app/README_PHASE7.md _to_review/streamlit_versions/ 2>/dev/null || true
mv streamlit_app/README_PHASE7_UI.md _to_review/streamlit_versions/ 2>/dev/null || true

# 4. 生成ディレクトリ
mkdir -p _to_review/generated
mv .bedrock_agentcore _to_review/generated/ 2>/dev/null || true
mv build _to_review/generated/ 2>/dev/null || true

# 5. 未使用ディレクトリ（内容確認後）
mkdir -p _to_review/unused
# mv cloudformation _to_review/unused/ 2>/dev/null || true
# mv gateway _to_review/unused/ 2>/dev/null || true
# mv docs _to_review/unused/ 2>/dev/null || true
# mv tests _to_review/unused/ 2>/dev/null || true

# 6. 開発用ファイル
mkdir -p _to_review/dev_files
mv .env.phase6.template _to_review/dev_files/ 2>/dev/null || true
mv docker-compose.yml _to_review/dev_files/ 2>/dev/null || true
mv Dockerfile _to_review/dev_files/ 2>/dev/null || true  # ルートのみ
mv streamlit_mcp_tools.py _to_review/dev_files/ 2>/dev/null || true

# 7. GitHub設定
mkdir -p _to_review/github
mv .github _to_review/github/ 2>/dev/null || true
```

## 確認が必要なディレクトリ

以下のディレクトリは内容を確認してから移動を決定:

1. **cloudformation/** - 使用されているか確認
2. **gateway/** - 使用されているか確認
3. **docs/** - 公開用ドキュメントがあるか確認
4. **tests/** - 必要なテストがあるか確認

## 注意事項

- 生成ファイル(.bedrock_agentcore.yaml, .gateway-config)は.gitignoreに追加済みなので移動不要
- lambda/invoker/layer/は巨大なので移動に時間がかかる可能性あり
- 移動後、スクリプト00-06を実行して動作確認すること
