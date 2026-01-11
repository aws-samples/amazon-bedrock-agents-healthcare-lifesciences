# SiLA2 Lab Automation Agent - Phase 4 アーキテクチャ

## システム全体図

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud Environment                           │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Streamlit UI (Port 8501)                      │ │
│  │                    ユーザーインターフェース                          │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                   │ HTTP                                 │
│                                   ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Amazon Bedrock AgentCore Runtime                      │ │
│  │                  (Agent Orchestration)                             │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                   │ API Call                             │
│                                   ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Amazon Bedrock AgentCore Gateway                      │ │
│  │                    (Tool Management)                               │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                   │ MCP Protocol                         │
│                                   │ (HTTP/8080)                          │
│                                   ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                  Application Load Balancer                         │ │
│  │                        (Internal ALB)                              │ │
│  │                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────┐    │ │
│  │  │  Listener: Port 8080 (HTTP)                              │    │ │
│  │  │  Health Check: /health (30s interval)                    │    │ │
│  │  └──────────────────────────────────────────────────────────┘    │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                   │                                      │
│                                   ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Target Group                                  │ │
│  │                    (IP Target Type)                                │ │
│  │  Health Check: /health, Healthy: 2/3, Unhealthy: 3/3              │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                   │                                      │
│                                   ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Amazon ECS Fargate                              │ │
│  │                  Cluster: sila2-bridge-dev                         │ │
│  │                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │              ECS Service (DesiredCount: 1)                   │ │ │
│  │  │                                                              │ │ │
│  │  │  ┌────────────────────────────────────────────────────────┐ │ │ │
│  │  │  │         ECS Task (Fargate)                             │ │ │ │
│  │  │  │         CPU: 256 (.25 vCPU)                            │ │ │ │
│  │  │  │         Memory: 512 MB                                 │ │ │ │
│  │  │  │                                                        │ │ │ │
│  │  │  │  ┌──────────────────────────────────────────────────┐ │ │ │ │
│  │  │  │  │    Bridge Container (Port 8080)                  │ │ │ │ │
│  │  │  │  │                                                  │ │ │ │ │
│  │  │  │  │  ┌────────────────────────────────────────────┐ │ │ │ │ │
│  │  │  │  │  │  MCP Server (FastAPI)                      │ │ │ │ │ │
│  │  │  │  │  │  - list_devices                            │ │ │ │ │ │
│  │  │  │  │  │  - get_device_status                       │ │ │ │ │ │
│  │  │  │  │  │  - execute_command                         │ │ │ │ │ │
│  │  │  │  │  └────────────────────────────────────────────┘ │ │ │ │ │
│  │  │  │  │                      │                          │ │ │ │ │
│  │  │  │  │                      ↓                          │ │ │ │ │
│  │  │  │  │  ┌────────────────────────────────────────────┐ │ │ │ │ │
│  │  │  │  │  │  gRPC Client                               │ │ │ │ │ │
│  │  │  │  │  │  (sila2_basic.proto)                       │ │ │ │ │ │
│  │  │  │  │  └────────────────────────────────────────────┘ │ │ │ │ │
│  │  │  │  └──────────────────────────────────────────────────┘ │ │ │ │
│  │  │  └────────────────────────────────────────────────────────┘ │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                   │ gRPC                                 │
│                                   │ (Port 50051-50053)                   │
│                                   ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Mock Device Lambdas                             │ │
│  │                    (開発・テスト用)                                  │ │
│  │                                                                    │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │ │
│  │  │  HPLC Device     │  │ Centrifuge Device│  │ Pipette Device  │ │ │
│  │  │  Lambda          │  │  Lambda          │  │  Lambda         │ │ │
│  │  │                  │  │                  │  │                 │ │ │
│  │  │  gRPC: 50051     │  │  gRPC: 50052     │  │  gRPC: 50053    │ │ │
│  │  │  Memory: 512MB   │  │  Memory: 512MB   │  │  Memory: 512MB  │ │ │
│  │  └──────────────────┘  └──────────────────┘  └─────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Supporting Services                             │ │
│  │                                                                    │ │
│  │  • Amazon ECR: sila2-bridge (Container Registry)                  │ │
│  │  • CloudWatch Logs: /ecs/sila2-bridge-dev (7日保持)                │ │
│  │  • VPC: Private Subnets (最低2つ)                                  │ │
│  │  • Security Groups: Port 8080 (Inbound), 443 (Outbound)           │ │
│  │  • IAM Roles: TaskExecutionRole, TaskRole                         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      Future: Edge Deployment                             │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Laboratory Edge Environment                           │ │
│  │                                                                    │ │
│  │  Bridge Container (同一イメージ) --[gRPC]--> 実機器                 │ │
│  │  - AWS IoT Greengrass                                              │ │
│  │  - ローカルネットワーク最適化                                         │ │
│  │  - オフライン動作対応                                                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## 通信フロー詳細

### 1. ユーザーリクエスト → デバイス実行
```
User (Streamlit UI)
  │
  │ HTTP Request: "List all SiLA2 devices"
  ↓
AgentCore Runtime
  │
  │ Agent Orchestration
  ↓
AgentCore Gateway
  │
  │ MCP Protocol (HTTP/8080)
  │ Tool: list_devices
  ↓
Application Load Balancer
  │
  │ Health Check: /health
  │ Route to healthy target
  ↓
Target Group
  │
  │ IP-based routing
  ↓
ECS Task (Fargate)
  │
  │ Container: Bridge (Port 8080)
  ↓
MCP Server (FastAPI)
  │
  │ Parse MCP request
  │ Validate tool schema
  ↓
gRPC Client
  │
  │ gRPC Call (Port 50051-50053)
  │ Proto: sila2_basic.proto
  ↓
Mock Device Lambda (HPLC/Centrifuge/Pipette)
  │
  │ Execute device command
  │ Return device status
  ↓
[Response flows back through the same path]
```

### 2. ヘルスチェックフロー
```
ALB Health Check (30秒間隔)
  │
  │ HTTP GET /health
  ↓
Bridge Container
  │
  │ Check: MCP Server running
  │ Check: gRPC Client ready
  ↓
Response: 200 OK
  │
  │ Healthy: 2/3 consecutive checks
  │ Unhealthy: 3/3 consecutive checks
  ↓
Target Group Status Update
```

## ネットワーク構成

```
┌─────────────────────────────────────────────────────────────┐
│                          VPC                                 │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Private Subnet 1 (AZ-a)                    ││
│  │                                                          ││
│  │  ┌──────────────────┐      ┌──────────────────┐        ││
│  │  │  ECS Task        │      │  ALB Target      │        ││
│  │  │  (Fargate)       │◄─────│  (IP: 10.0.1.x)  │        ││
│  │  └──────────────────┘      └──────────────────┘        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Private Subnet 2 (AZ-b)                    ││
│  │                                                          ││
│  │  ┌──────────────────┐      ┌──────────────────┐        ││
│  │  │  ECS Task        │      │  ALB Target      │        ││
│  │  │  (Standby)       │◄─────│  (IP: 10.0.2.x)  │        ││
│  │  └──────────────────┘      └──────────────────┘        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  Security Group                          ││
│  │                                                          ││
│  │  Inbound:  Port 8080 (MCP from Gateway)                 ││
│  │  Outbound: Port 443  (HTTPS to Lambda Function URLs)    ││
│  │            Port 50051-50053 (gRPC to Mock Devices)      ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## コンポーネント詳細

### ECS Fargate Task
- **Launch Type**: FARGATE
- **CPU**: 256 (.25 vCPU)
- **Memory**: 512 MB
- **Network Mode**: awsvpc
- **Assign Public IP**: ENABLED

### Application Load Balancer
- **Type**: Application Load Balancer
- **Scheme**: Internal
- **Port**: 8080 (HTTP)
- **Health Check**: /health (30秒間隔)

### Target Group
- **Target Type**: IP
- **Port**: 8080
- **Protocol**: HTTP
- **Health Check Path**: /health
- **Healthy Threshold**: 2/3
- **Unhealthy Threshold**: 3/3

### Bridge Container
- **Base Image**: python:3.11-slim
- **Exposed Port**: 8080
- **MCP Tools**:
  - list_devices
  - get_device_status
  - execute_command
- **gRPC Ports**: 50051-50053

### Mock Device Lambdas
- **HPLC Device**: Port 50051
- **Centrifuge Device**: Port 50052
- **Pipette Device**: Port 50053
- **Memory**: 512 MB (gRPC対応)
- **Environment**: GRPC_ENABLED=true

## デプロイフロー

```
Step 01: Infrastructure Setup
  ├─ VPC作成
  ├─ Subnets作成 (最低2つ)
  └─ Security Groups作成

Step 02: Mock Devices
  ├─ HPLC Lambda作成
  ├─ Centrifuge Lambda作成
  └─ Pipette Lambda作成

Step 03: Build Bridge Container
  ├─ Docker build
  ├─ ECR login
  └─ ECR push

Step 04: Deploy Bridge Container
  ├─ ECS Cluster作成
  ├─ Task Definition作成
  ├─ ALB作成
  ├─ Target Group作成
  └─ ECS Service作成

Step 05: Enable Device gRPC
  ├─ Lambda環境変数更新 (GRPC_ENABLED=true)
  └─ 3デバイス一括更新

Step 06: Update Gateway Target
  ├─ 既存Lambda Target削除
  └─ 新規MCP Target作成

Step 07: Deploy AgentCore Runtime
  └─ Runtime + Gateway設定

Step 09: Setup UI
  └─ Streamlit UI起動

Step 10: Run Tests
  └─ 統合テスト実行
```

## コスト構成

### 月額コスト (24時間稼働)
- **ECS Fargate**: $24/月
  - CPU (0.25 vCPU): $0.04048/h × 730h = $29.55
  - Memory (0.5 GB): $0.004445/h × 730h = $3.24
- **ALB**: $16/月
  - 固定費: $0.0225/h × 730h = $16.43
- **Mock Device Lambdas**: $15/月
- **CloudWatch Logs**: $2/月
- **ECR**: $1/月

**合計**: 約 $58/月

### コスト最適化オプション
- ECS Service停止時: $0/月 (Lambda + ECR のみ)
- オンデマンド起動: 必要時のみECS起動

## セキュリティ

### IAM Roles
- **TaskExecutionRole**: ECR/CloudWatch アクセス
- **TaskRole**: Lambda呼び出し権限

### Network Security
- **Internal ALB**: VPC内部のみアクセス可能
- **Security Group**: 最小権限の原則
- **Private Subnets**: インターネット直接アクセス不可

### Container Security
- **ECR Image Scanning**: 有効
- **Read-only Root Filesystem**: 推奨
- **Non-root User**: 実装済み

## モニタリング

### CloudWatch Metrics
- ECS Service CPU/Memory使用率
- ALB Request Count
- Target Health Status
- Container Insights

### CloudWatch Logs
- ECS Task Logs: /ecs/sila2-bridge-dev
- Retention: 7日間

### Health Checks
- ALB → Target Group: 30秒間隔
- Container Health Check: /health エンドポイント
