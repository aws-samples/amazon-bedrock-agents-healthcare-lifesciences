# AWS デプロイメントガイド - SiLA2 Lab Automation Agent

## 🎯 概要

各フェーズでAWS環境にデプロイして段階的に動作確認を行うガイドです。

## 🚀 フェーズ別デプロイメント

### Phase 1: MCP統合基盤デプロイ ✅ **完了**

#### 前提条件
```bash
# AWS CLI設定確認
aws sts get-caller-identity

# 必要な権限
# - CloudFormation: Full Access
# - Lambda: Full Access  
# - IAM: Role/Policy作成権限
# - Bedrock: Model Access
```

#### デプロイ手順
```bash
# 1. Phase 1デプロイ
bash deploy-phase1-mcp.sh

# 2. デプロイ状況確認
aws cloudformation describe-stacks \
  --stack-name sila2-agent-phase1-mcp \
  --query 'Stacks[0].StackStatus'

# 3. AgentCore設定
source .venv/bin/activate
agentcore configure --entrypoint main_mcp.py --name sila2_agent_phase1

# 4. デプロイ
agentcore launch
```

#### 動作確認テスト
```bash
# 基本接続テスト
agentcore invoke '{"prompt": "Check MCP connection status"}'

# SiLA2ツールテスト
agentcore invoke '{"prompt": "Check device HPLC-01 status via MCP"}'

# エラーハンドリングテスト
agentcore invoke '{"prompt": "Test invalid device connection"}'
```

#### 検証項目
- [ ] CloudFormation スタック正常作成
- [ ] Lambda 関数デプロイ成功
- [ ] MCP Server 起動確認
- [ ] AgentCore → MCP → SiLA2 Tools 通信成功
- [ ] CloudWatch ログ出力確認
- [ ] エラーハンドリング動作確認

---

### Phase 2: AgentCore Gatewayデプロイ ✅ **完了**

#### 前提条件
```bash
# Phase 1完了確認
aws cloudformation describe-stacks --stack-name sila2-agent-phase1-mcp

# 必要権限
# - Bedrock AgentCore: Full Access
# - Lambda: Full Access (Gateway Tools用)
# - IAM: Role/Policy作成権限
```

#### デプロイ手順
```bash
# 1. AgentCore Gateway統合デプロイ
./deploy-agentcore-gateway.sh

# 2. AgentCore Gateway状態確認
agentcore gateway status --name sila2-lab-automation-gateway

# 3. Gateway Tools確認
agentcore gateway list-tools --name sila2-lab-automation-gateway
```

#### 動作確認テスト
```bash
# 基本デバイスリストテスト
agentcore invoke '{"prompt": "List all available SiLA2 devices"}'

# デバイス状態テスト
agentcore invoke '{"prompt": "What is the status of HPLC-01?"}'

# コマンド実行テスト
agentcore invoke '{"prompt": "Start a measurement on PIPETTE-01"}'

# Gateway Tools直接テスト
agentcore gateway invoke-tool \
  --gateway-name sila2-lab-automation-gateway \
  --tool-name list_available_devices
```

#### 検証項目
- [x] AgentCore Gateway正常作成 ✅
- [x] AgentCore Runtime正常起動 ✅
- [x] Gateway Tools通信成功 ✅
- [x] SiLA2ツール実行確認 ✅
- [x] AgentCore invoke動作確認 ✅
- [x] ネイティブ統合動作確認 ✅

---

### Phase 3: SiLA2 Protocol実装デプロイ 🚧 **次のフェーズ**

#### 前提条件
```bash
# Phase 2完了確認
aws cloudformation describe-stacks --stack-name sila2-agent-phase2-gateway

# Lambda Mock Device準備
# - API Gateway + Lambda設定
# - 統一Mock Device Lambda設定
```

#### デプロイ手順
```bash
# 1. Phase 3デプロイ (Lambda Mock Devices)
bash deploy-phase3-lambda-mock-devices.sh

# 2. 統一Mock Device Lambda設定
aws ssm put-parameter \
  --name "/sila2-agent/mock-devices/config" \
  --value '{"devices": {"hplc": ["HPLC-01"], "centrifuge": ["CENTRIFUGE-01"], "pipette": ["PIPETTE-01"]}}' \
  --type "String"

# 3. Lambda関数確認
aws lambda get-function --function-name sila2-unified-mock-device

# 4. API Gateway設定確認
aws apigateway get-rest-apis --query 'items[?name==`sila2-mock-devices-api`]'
```

#### 動作確認テスト
```bash
# 統一Mock Device Lambdaテスト
agentcore invoke '{"prompt": "List all mock SiLA2 devices"}'
agentcore invoke '{"prompt": "Execute sample prep on mock HPLC"}'

# API Gateway + Lambda統合テスト
agentcore invoke '{"prompt": "Check mock device status via unified Lambda"}'
agentcore invoke '{"prompt": "Test device factory pattern"}'

# 複数デバイス同時テスト
agentcore invoke '{"prompt": "Execute multi-device protocol on mock devices"}'

# Lambda直接テスト
aws lambda invoke \
  --function-name sila2-unified-mock-device \
  --payload '{"pathParameters": {"device_type": "hplc", "device_id": "HPLC-01", "action": "get_status"}}' \
  response.json
```

#### 検証項目
- [ ] API Gateway + 統一Lambda統合成功
- [ ] デバイスファクトリーパターン動作確認
- [ ] 複数デバイスタイプ対応確認
- [ ] エラーハンドリング動作確認
- [ ] Lambda関数パフォーマンス確認

---

### Phase 4: Tecan Fluent統合デプロイ ⏳

#### 前提条件
```bash
# 全Phase完了確認
aws cloudformation describe-stacks --stack-name sila2-agent-phase3-fluent

# 本番環境準備
# - 監視・アラート設定
# - セキュリティ設定
# - バックアップ設定
```

#### デプロイ手順
```bash
# 1. 本番環境デプロイ
bash deploy-phase4-production.sh

# 2. 監視設定
aws cloudwatch put-metric-alarm \
  --alarm-name "SiLA2-Agent-Errors" \
  --alarm-description "SiLA2 Agent Error Rate" \
  --metric-name "Errors" \
  --namespace "AWS/Lambda" \
  --statistic "Sum" \
  --period 300 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold"

# 3. 統合テスト実行
bash test-integration-aws.sh
```

#### 動作確認テスト
```bash
# エンドツーエンドテスト
agentcore invoke '{"prompt": "Execute full lab automation workflow"}'

# 負荷テスト
for i in {1..10}; do
  agentcore invoke '{"prompt": "Check all device status"}' &
done
wait

# 障害テスト
# Lambda関数停止→自動復旧確認
# Greengrass接続断→再接続確認
```

#### 検証項目
- [ ] 全フェーズ機能統合動作確認
- [ ] 本番環境パフォーマンス確認
- [ ] 監視・アラート動作確認
- [ ] セキュリティ設定確認
- [ ] 障害回復機能確認
- [ ] 他エージェントとの統一感確認

---

## 🔧 デプロイスクリプト

### deploy-phase1-mcp.sh
```bash
#!/bin/bash
set -e
echo "🚀 Phase 1: MCP統合基盤デプロイ"

# CloudFormation デプロイ
aws cloudformation deploy \
  --template-file infra/cfn-mcp-integration.yaml \
  --stack-name sila2-agent-phase1-mcp \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    AgentName=sila2-agent-phase1

# AgentCore設定・デプロイ
source .venv/bin/activate
agentcore configure --entrypoint main_mcp.py --name sila2_agent_phase1
agentcore launch

echo "✅ Phase 1 デプロイ完了"
```

### deploy-phase3-lambda-mock-devices.sh
```bash
#!/bin/bash
set -e
echo "🚀 Phase 3: Lambda Mock Devices デプロイ"

# CloudFormation デプロイ (統一Lambda)
aws cloudformation deploy \
  --template-file infra/cfn-lambda-mock-devices.yaml \
  --stack-name sila2-agent-phase3-lambda-mock \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    LambdaFunctionName=sila2-unified-mock-device \
    ApiGatewayName=sila2-mock-devices-api

# Lambda関数コードデプロイ
zip -r mock-device-lambda.zip src/mock_devices/
aws lambda update-function-code \
  --function-name sila2-unified-mock-device \
  --zip-file fileb://mock-device-lambda.zip

# API Gateway設定更新
aws apigateway create-deployment \
  --rest-api-id $(aws apigateway get-rest-apis --query 'items[?name==`sila2-mock-devices-api`].id' --output text) \
  --stage-name prod

echo "✅ Phase 3 Lambda Mock Devices デプロイ完了"
```

### deploy-agentcore-gateway.sh (最新版)
```bash
#!/bin/bash
set -e
echo "🚀 Phase 2: AgentCore Gateway統合デプロイ"

# AgentCore Gateway作成
agentcore gateway create \
  --name sila2-lab-automation-gateway \
  --type native \
  --tools-config gateway-tools-config.json

# Gateway Tools設定
agentcore gateway add-tools \
  --gateway-name sila2-lab-automation-gateway \
  --tools sila2_bridge_tools.py

# AgentCore Runtimeデプロイ
agentcore configure \
  --entrypoint main_agentcore_native.py \
  --name sila2_agent \
  --gateway sila2-lab-automation-gateway

agentcore launch

echo "✅ Phase 2 デプロイ完了"
```

### test-integration-aws.sh
```bash
#!/bin/bash
set -e
echo "🧪 AWS統合テスト実行"

# 基本機能テスト
echo "基本機能テスト..."
agentcore invoke '{"prompt": "Check all systems status"}'

# Lambda Mock Deviceテスト
echo "Lambda Mock Deviceテスト..."
agentcore invoke '{"prompt": "List all mock devices via unified Lambda"}'
agentcore invoke '{"prompt": "Test HPLC simulator functionality"}'

# パフォーマンステスト
echo "パフォーマンステスト..."
time agentcore invoke '{"prompt": "Execute performance test protocol"}'

# エラーハンドリングテスト
echo "エラーハンドリングテスト..."
agentcore invoke '{"prompt": "Test error recovery scenarios"}'

# Lambda直接テスト
echo "Lambda直接テスト..."
aws lambda invoke \
  --function-name sila2-unified-mock-device \
  --payload '{"pathParameters": {"device_type": "hplc", "device_id": "HPLC-01", "action": "get_status"}}' \
  test-response.json
cat test-response.json

echo "✅ 統合テスト完了"
```

---

## 📊 監視・メトリクス

### CloudWatch メトリクス
- **Lambda実行時間**: 各フェーズの応答時間
- **エラー率**: 失敗したリクエストの割合
- **スループット**: 1分あたりのリクエスト数
- **Greengrass接続状態**: デバイス接続ステータス

### アラート設定
- **高エラー率**: 5分間で5回以上のエラー
- **高レイテンシ**: 応答時間30秒超過
- **接続断**: Greengrass接続失敗

### ログ監視
- **AgentCore**: `/aws/bedrock-agentcore/sila2-agent`
- **Lambda**: `/aws/lambda/sila2-mcp-server`
- **Greengrass**: `/aws/greengrass/sila2-gateway`

---

## 🧹 クリーンアップ

### フェーズ別クリーンアップ
```bash
# Phase 2クリーンアップ (AgentCore Gateway)
agentcore delete --name sila2_agent
agentcore gateway delete --name sila2-lab-automation-gateway

# Phase 1クリーンアップ
agentcore delete --name sila2_agent_phase1
aws cloudformation delete-stack --stack-name sila2-agent-phase1-mcp
```

### 完全クリーンアップ
```bash
bash cleanup-all-phases.sh
```

---

**最終更新**: 2025-01-XX  
**次回更新**: フェーズ完了時