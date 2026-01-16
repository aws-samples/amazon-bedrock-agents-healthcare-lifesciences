# SiLA2 Lab Automation Agent - Phase 4 Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud Environment                           │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Streamlit UI (Port 8501)                      │ │
│  │                       User Interface                               │ │
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
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │  Listener: Port 8080 (HTTP)                                  │ │ │
│  │  │  Health Check: /health (30s interval)                        │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
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
│  │                    (Development/Testing)                           │ │
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
│  │  • CloudWatch Logs: /ecs/sila2-bridge-dev (7-day retention)       │ │
│  │  • VPC: Private Subnets (minimum 2)                                │ │
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
│  │  Bridge Container (same image) --[gRPC]--> Physical Devices       │ │
│  │  - AWS IoT Greengrass                                              │ │
│  │  - Local network optimization                                      │ │
│  │  - Offline operation support                                       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Communication Flow Details

### 1. User Request → Device Execution
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

### 2. Health Check Flow
```
ALB Health Check (30-second interval)
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

## Network Configuration

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

## Component Details

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
- **Health Check**: /health (30-second interval)

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
- **Memory**: 512 MB (gRPC support)
- **Environment**: GRPC_ENABLED=true

## Deployment Flow

```
Step 01: Infrastructure Setup
  ├─ Create VPC
  ├─ Create Subnets (minimum 2)
  └─ Create Security Groups

Step 02: Mock Devices
  ├─ Create HPLC Lambda
  ├─ Create Centrifuge Lambda
  └─ Create Pipette Lambda

Step 03: Build Bridge Container
  ├─ Docker build
  ├─ ECR login
  └─ ECR push

Step 04: Deploy Bridge Container
  ├─ Create ECS Cluster
  ├─ Create Task Definition
  ├─ Create ALB
  ├─ Create Target Group
  └─ Create ECS Service

Step 05: Enable Device gRPC
  ├─ Update Lambda environment variables (GRPC_ENABLED=true)
  └─ Batch update 3 devices

Step 06: Update Gateway Target
  ├─ Remove existing Lambda Target
  └─ Create new MCP Target

Step 07: Deploy AgentCore Runtime
  └─ Configure Runtime + Gateway

Step 09: Setup UI
  └─ Launch Streamlit UI

Step 10: Run Tests
  └─ Execute integration tests
```

## Cost Structure

### Monthly Cost (24/7 operation)
- **ECS Fargate**: $24/month
  - CPU (0.25 vCPU): $0.04048/h × 730h = $29.55
  - Memory (0.5 GB): $0.004445/h × 730h = $3.24
- **ALB**: $16/month
  - Fixed cost: $0.0225/h × 730h = $16.43
- **Mock Device Lambdas**: $15/month
- **CloudWatch Logs**: $2/month
- **ECR**: $1/month

**Total**: Approximately $58/month

### Cost Optimization Options
- ECS Service stopped: $0/month (Lambda + ECR only)
- On-demand startup: Start ECS only when needed

## Security

### IAM Roles
- **TaskExecutionRole**: ECR/CloudWatch access
- **TaskRole**: Lambda invocation permissions

### Network Security
- **Internal ALB**: VPC-internal access only
- **Security Group**: Principle of least privilege
- **Private Subnets**: No direct internet access

### Container Security
- **ECR Image Scanning**: Enabled
- **Read-only Root Filesystem**: Recommended
- **Non-root User**: Implemented

## Monitoring

### CloudWatch Metrics
- ECS Service CPU/Memory utilization
- ALB Request Count
- Target Health Status
- Container Insights

### CloudWatch Logs
- ECS Task Logs: /ecs/sila2-bridge-dev
- Retention: 7 days

### Health Checks
- ALB → Target Group: 30-second interval
- Container Health Check: /health endpoint
