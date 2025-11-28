# SiLA2 Agent Deployment Order (Phase 4)
## MCP + gRPC + Service Discovery Architecture

**更新日**: 2025-01-28  
**アーキテクチャ**: Bridge Container + Mock Device Container (ECS Fargate)

---

## 📋 Prerequisites

- AWS CLI configured
- Docker installed and running
- Python 3.9+
- Valid AWS credentials

---

## 🔧 Environment Variables

```bash
export AWS_REGION=us-east-1
export ENV_NAME=dev
export GATEWAY_ID=<your-gateway-id>
export STACK_NAME=sila2-bridge-ecs
```

---

## 🚀 Deployment Steps

### Step 1: Infrastructure Setup
```bash
./scripts/01_setup_infrastructure.sh
```
**内容**: VPC, Subnet, Security Group基盤

### Step 2: Build Containers
```bash
./scripts/02_build_containers.sh
```
**内容**: 
- Bridge Container (MCP Server + gRPC Client)
- Mock Device Container (3デバイス統合gRPCサーバー)
- ECRプッシュ

### Step 3: Deploy ECS Service Discovery
```bash
./scripts/03_deploy_ecs.sh
```
**内容**:
- ECS Cluster作成
- Bridge Service (Service Discovery)
- Mock Device Service (Service Discovery)
- Security Groups
- CloudWatch Logs

### Step 4: Deploy AgentCore Runtime
```bash
./scripts/04_deploy_agentcore.sh
```
**内容**: AgentCore Runtime/Gateway デプロイ

### Step 5: Update Gateway Target
```bash
GATEWAY_ID=<gateway-id> ./scripts/05_update_gateway_target.sh
```
**内容**: MCP Target作成 (Service Discovery endpoint)

### Step 6: Run Tests
```bash
./scripts/06_run_tests.sh
```
**内容**: End-to-End統合テスト

### Step 7: Setup UI (Optional)
```bash
./scripts/07_setup_ui.sh
```
**内容**: Streamlit UI

---

## ⚡ Full Deployment

```bash
GATEWAY_ID=<gateway-id> ./scripts/deploy_all.sh
```

---

## ✅ Verification

### 1. Check ECS Services
```bash
aws ecs describe-services \
  --cluster sila2-bridge-dev \
  --services sila2-bridge-dev sila2-mock-devices-dev
```

### 2. Test Bridge Endpoint
```bash
ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name sila2-bridge-ecs \
  --query 'Stacks[0].Outputs[?OutputKey==`BridgeServiceEndpoint`].OutputValue' \
  --output text)

curl $ENDPOINT/health
```

### 3. Test Service Discovery
```bash
nslookup bridge.sila2.local
nslookup mock-devices.sila2.local
```

### 4. Test MCP Tools
```bash
curl -X POST $ENDPOINT/tools/list_devices
```

---

## 🔄 Rollback

### Stop ECS Services
```bash
aws ecs update-service \
  --cluster sila2-bridge-dev \
  --service sila2-bridge-dev \
  --desired-count 0

aws ecs update-service \
  --cluster sila2-bridge-dev \
  --service sila2-mock-devices-dev \
  --desired-count 0
```

### Delete Stack
```bash
aws cloudformation delete-stack --stack-name sila2-bridge-ecs
```

---

## 📊 Architecture

```
AgentCore Gateway
    ↓ (MCP)
Bridge Container (bridge.sila2.local:8080)
    ↓ (gRPC)
Mock Device Container (mock-devices.sila2.local:50051)
    ├── HPLC
    ├── Centrifuge
    └── Pipette
```

---

## 💰 Cost

| リソース | 月額 |
|---------|------|
| ECS Fargate (Bridge) | $7 |
| ECS Fargate (Mock) | $7 |
| CloudWatch Logs | $2 |
| **合計** | **$16** |

**削減**: ALB削除で$16/月削減 (50%)

---

## 🗂️ Archived Scripts

Phase 3関連スクリプトは `archive/phase3-scripts/` に移動:
- `02_deploy_mock_devices.sh` - Mock Device Lambda (不要)
- `05_enable_device_grpc.sh` - Lambda gRPC有効化 (不要)
- `15_migrate_to_service_discovery.sh` - 移行専用
- `03_build_bridge_container.sh` - 統合済み
- `04_deploy_bridge_container.sh` - 置き換え
- `11_build_mock_device_container.sh` - 統合済み

---

## 📝 Notes

- **Service Discovery**: VPC内部DNS使用
- **ALB不要**: コスト削減、レイテンシ改善
- **完全gRPC**: Lambda制約解消
- **エッジ対応**: 同一コンテナイメージ使用可能
