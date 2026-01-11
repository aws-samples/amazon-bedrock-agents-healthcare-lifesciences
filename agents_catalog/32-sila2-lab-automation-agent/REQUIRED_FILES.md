# 必須ファイル一覧（スクリプト00-06で参照）

## デプロイスクリプト
```
scripts/00_setup_vpc_endpoint.sh
scripts/01_setup_infrastructure.sh
scripts/02_build_containers.sh
scripts/03_deploy_ecs.sh
scripts/04_create_gateway.sh
scripts/05_create_mcp_target.sh
scripts/06_deploy_agentcore.sh
scripts/utils/common.sh
scripts/utils/aws_helpers.sh
scripts/utils/validation.sh
```

## インフラストラクチャ定義
```
infrastructure/bridge_container_ecs_no_alb.yaml
infrastructure/lambda_proxy.yaml
infrastructure/phase6-cfn.yaml
```

## Bridge Container
```
bridge_container/Dockerfile
bridge_container/requirements.txt
bridge_container/bridge_server.py
bridge_container/proto/sila2_basic_pb2.py
bridge_container/proto/sila2_basic_pb2_grpc.py
bridge_container/proto/sila2_streaming_pb2.py
bridge_container/proto/sila2_streaming_pb2_grpc.py
bridge_container/proto/sila2_tasks_pb2.py
bridge_container/proto/sila2_tasks_pb2_grpc.py
bridge_container/proto/__init__.py
```

## Mock Devices
```
mock_devices/Dockerfile
mock_devices/requirements.txt
mock_devices/mock_server.py
mock_devices/proto/sila2_basic_pb2.py
mock_devices/proto/sila2_basic_pb2_grpc.py
mock_devices/proto/sila2_streaming_pb2.py
mock_devices/proto/sila2_streaming_pb2_grpc.py
mock_devices/proto/sila2_tasks_pb2.py
mock_devices/proto/sila2_tasks_pb2_grpc.py
mock_devices/proto/__init__.py
```

## Proto定義（ソース）
```
proto/sila2_basic.proto
proto/sila2_streaming.proto
proto/sila2_tasks.proto
proto/sila2_basic_pb2.py
proto/sila2_basic_pb2_grpc.py
proto/sila2_streaming_pb2.py
proto/sila2_streaming_pb2_grpc.py
proto/sila2_tasks_pb2.py
proto/sila2_tasks_pb2_grpc.py
proto/__init__.py
```

## Lambda Proxy
```
lambda_proxy/index.py
lambda_proxy/requirements.txt
```

## Lambda Invoker
```
lambda/invoker/lambda_function.py
lambda/invoker/requirements.txt
```

## Lambda Tools
```
lambda/tools/analyze_heating_rate/index.py
lambda/tools/analyze_heating_rate/requirements.txt
```

## AgentCore設定
```
agentcore/agent_instructions.txt
agentcore/gateway_config.py
agentcore/runtime_config.py
agentcore/verify_setup.py
```

## メインアプリケーション
```
main_agentcore_phase3.py
requirements.txt
```

## 設定ファイル（公開不可）
```
.dockerignore
.gitignore
```

## 生成ファイル（スクリプトで自動生成、リポジトリ不要）
```
.bedrock_agentcore.yaml  # 06で生成
.gateway-config          # 04で生成
```

## オプション（Streamlit UI）
```
streamlit_app/phase7_final.py
streamlit_app/requirements.txt
streamlit_app/Dockerfile
streamlit_app/QUICKSTART.md
```

## ドキュメント（作成予定）
```
README.md
ARCHITECTURE.md
DEPLOYMENT.md
```

---

## 削除対象（_to_review/に移動済み）

### 開発フェーズドキュメント
- _to_review/phase_docs/ 配下の全PHASE*.md

### 重複Streamlitアプリ
- _to_review/streamlit_versions/ 配下の全.pyファイル

### テストスクリプト
- _to_review/test_scripts/ 配下の全.shファイル
- _to_review/python_tests/ 配下の全.pyファイル

### 未使用デプロイスクリプト
- _to_review/deploy_scripts/ 配下の全.shファイル

### ヘルパースクリプト
- _to_review/helper_scripts/ 配下の全ファイル

### バックアップ
- _to_review/backup/ 配下の全ファイル

### ログ
- _to_review/logs/ 配下の全ファイル

### 一時ファイル
- _to_review/temp/ 配下の全ファイル

### 機密情報（公開前削除必須）
- _to_review/secrets/ 配下の全ファイル

---

## 追加削除対象（まだ残存）

### ビルド成果物
```
lambda/lambda_invoker.zip
lambda/invoker/layer/  # 自動生成されるため不要
```

### 開発用キャッシュ
```
.pytest_cache/
.venv/
.python-version
```

### 重複README
```
streamlit_app/README_DEMO.md
streamlit_app/README_PHASE7.md
streamlit_app/README_PHASE7_UI.md
```

### 設定ファイル（開発用）
```
.env.phase6.template  # テンプレートとして残すか検討
docker-compose.yml    # 開発用、公開するか検討
```

### その他
```
.bedrock_agentcore/  # AgentCore生成ディレクトリ
.github/             # GitHub設定（内容確認必要）
```
