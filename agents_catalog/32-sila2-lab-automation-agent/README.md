# SiLA2 Lab Automation Agent

**Phase 7 Complete** ✅ - AI自律制御 + Memory統合による完全自動化実現

## 🎯 Current Status: Phase 7

- ✅ **2 Targets構成**: Container (SiLA2変換) + Lambda (計算)
- ✅ **6 Tools統合**: Phase 4 (4個) + Phase 7 (2個)
- ✅ **Memory管理**: 温度設定時の初期化 + 手動制御記録
- ✅ **AI自律判断**: scenario情報なしで自己判断
- ✅ **Streamlit UI**: Memory表示 + AI判断履歴可視化
- 🔄 **ドキュメント整備中**: Step 3進行中
- ⬜ **統合テスト**: Step 4未着手

## 🚀 Quick Deploy

```bash
cd scripts
export AWS_REGION=us-west-2

# Phase 1: ECRとコンテナイメージ
./01_setup_ecr_and_build.sh

# Phase 2: Lambdaパッケージ
./02_package_lambdas.sh

# Phase 3: メインスタックデプロイ
./03_deploy_stack.sh --vpc-id vpc-xxxxx --subnet-ids subnet-xxxxx,subnet-yyyyy

# Phase 4: AgentCore Runtime
./04_deploy_agentcore.sh

# UI起動
cd ../streamlit_app
streamlit run app.py
```

詳細は [DEPLOYMENT_GUIDE.md](scripts/DEPLOYMENT_GUIDE.md) を参照してください。

## 🏗️ Architecture (Phase 7)

```
User/Lambda Invoker → AgentCore Runtime → MCP Gateway (2 Targets)
                                           ├─ Target 1: Bridge Container (5 tools)
                                           │   └─ Mock Devices (ECS)
                                           └─ Target 2: Lambda (1 tool)
```

- **Framework**: Amazon Bedrock AgentCore
- **Model**: Anthropic Claude 3.5 Sonnet v2
- **Gateway**: MCP Gateway (2 Targets構成)
- **Memory**: Built-in Session Memory
- **Infrastructure**: ECS Fargate + Lambda + VPC Endpoint
- **Mock Devices**: HPLC (scenario切り替え対応)
- **UI**: Streamlit (Memory表示 + AI判断履歴)

## 🔧 Available Tools (Phase 7)

### Target 1: Bridge Container (5 tools)
- `list_devices()`: デバイス一覧取得
- `get_device_status(device_id)`: デバイス状態確認
- `get_task_status(device_id, task_id)`: タスク状態確認
- `get_property(device_id, property_name)`: プロパティ取得
- `execute_control(device_id, command, parameters)`: SiLA2制御実行
  - set_temperature: 温度設定
  - abort_experiment: 実験中止

### Target 2: Lambda (1 tool)
- `analyze_heating_rate(device_id, history)`: 温度上昇率計算

## 📁 Key Files (Phase 7)

### Deployment Scripts
- `scripts/01_setup_ecr_and_build.sh` - ECRリポジトリ作成 + コンテナビルド
- `scripts/02_package_lambdas.sh` - Lambda関数パッケージ
- `scripts/03_deploy_stack.sh` - メインスタック (ECS/Lambda/Gateway/SNS/EventBridge)
- `scripts/04_deploy_agentcore.sh` - AgentCore Runtime + Memory
- `scripts/DEPLOYMENT_GUIDE.md` - 詳細デプロイ手順

### Infrastructure
- `infrastructure/bridge_container_ecs_no_alb.yaml` - ECS Fargate
- `infrastructure/lambda_proxy.yaml` - Lambda Proxy
- `src/bridge/mcp_server.py` - MCP Bridge (execute_control追加)
- `src/lambda/tools/analyze_heating_rate/` - 温度上昇率計算Lambda
- `src/lambda/invoker/lambda_function.py` - Lambda Invoker (Memory管理)

### Application
- `agentcore/agent_instructions.txt` - AI自律判断版Instructions
- `.bedrock_agentcore.yaml` - AgentCore設定
- `streamlit_app/app.py` - Streamlit UI (Memory表示)
- `PHASE7_OVERVIEW.md` - Phase 7概要
- `PHASE7_ARCHITECTURE.md` - Phase 7アーキテクチャ

## 🎯 Phase 7 Achievements

- ✅ **2 Targets構成**: Container (SiLA2変換) + Lambda (計算) の責任分離
- ✅ **execute_control統合**: 手動・自律制御を単一ツールで実現
- ✅ **Memory管理**: 温度設定時の初期化 + 手動制御記録
- ✅ **AI自律判断**: scenario情報なしで自己判断
- ✅ **制御競合回避**: 手動制御後5分は自律制御を抑制
- ✅ **Streamlit UI拡張**: Memory表示 + AI判断履歴可視化
- ✅ **VPCエンドポイント**: Bedrock AgentCore API用
- ✅ **不要Lambda削除**: Gateway統一により個別Lambda不要
- 🔄 **ドキュメント整備**: Step 3進行中
- ⬜ **統合テスト**: Step 4未着手

## 🧪 Example Usage (Phase 7)

### 手動制御
```bash
# 温度設定 (Memory初期化 + 実験ルール注入)
agentcore invoke '{"prompt": "HPLC_001の温度を80度に設定"}'

# デバイス状態確認
agentcore invoke '{"prompt": "HPLC_001の現在の状態は?"}'
```

### 自律分析 (Lambda Invoker経由)
```bash
# 定期分析 (5分毎)
aws lambda invoke \
  --function-name sila2-agentcore-invoker \
  --payload '{"action": "periodic", "devices": ["hplc_001"]}' \
  response.json

# 結果確認
cat response.json
```

**Expected Response**:
```json
{
  "analysis": {
    "heating_rate": 2.0,
    "expected_rate": 10.0,
    "is_anomaly": true,
    "scenario_mode": "scenario_2"
  },
  "decision": "温度上昇が遅いため、温度再設定で復帰",
  "action_taken": "set_temperature",
  "reasoning": "scenario_2検知、scenario_1への復帰が必要"
}
```

## 📋 Prerequisites (Phase 7)

- AWS CLI configured with appropriate permissions
- Python 3.9+
- Docker (for AgentCore Runtime)
- Required AWS services access:
  - Amazon Bedrock AgentCore
  - AWS Lambda
  - Amazon ECR
  - Amazon ECS
  - Amazon VPC (VPCエンドポイント必須)
  - AWS CloudFormation

### VPC Requirements (Phase 7新規)

Lambda InvokerがVPC内に配置されるため、Bedrock AgentCore APIへのアクセスにVPCエンドポイントが必要:

```bash
# VPCエンドポイント作成
./scripts/00_setup_vpc_endpoint.sh
```

**または** NAT Gateway (非推奨、コスト高):
- 追加コスト: ~$32/月
- VPCエンドポイント推奨: ~$7/月

## 🔄 Next Steps

### Step 3: ドキュメント整備 (進行中)
- ✅ PHASE7_OVERVIEW.md更新
- ✅ PHASE7_ARCHITECTURE.md更新
- ✅ README.md更新

### Step 4: 統合テスト (未着手)
- ⬜ Gateway経由ツール動作確認
- ⬜ Memory動作確認
- ⬜ AI自律制御E2Eテスト

### Future Enhancements
- Real SiLA2 gRPC protocol implementation
- Physical device integration
- Production deployment optimization
- Advanced error handling and monitoring

## 📚 Documentation

- `PHASE7_OVERVIEW.md` - Phase 7概要と実装状況
- `PHASE7_ARCHITECTURE.md` - 詳細アーキテクチャ設計
- `PHASE7_DEPLOYMENT_PLAN.md` - デプロイ手順
- `HANDOVER_NOTES.md` - 実装タスク一覧と進捗
- `DEPLOYMENT_VALIDATION.md` - デプロイ検証手順