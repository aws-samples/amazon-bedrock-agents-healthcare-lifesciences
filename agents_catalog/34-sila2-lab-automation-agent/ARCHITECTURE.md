# SiLA2 Lab Automation Agent - Architecture

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
│  │                  Claude 3.5 Sonnet v2                              │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                   │ API Call                             │
│                                   ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Amazon Bedrock AgentCore Gateway                      │ │
│  │                    (Multi-Target Routing)                          │ │
│  │                                                                    │ │
│  │  Target 1: MCP Bridge (10 tools)                                  │ │
│  │  Target 2: Analysis Lambda (1 tool)                               │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                   │                                      │
│                    ┌──────────────┴──────────────┐                      │
│                    │                             │                      │
│                    ↓                             ↓                      │
│  ┌─────────────────────────────┐  ┌──────────────────────────────────┐ │
│  │   MCP Bridge Container      │  │   Analysis Lambda                │ │
│  │   (ECS Fargate)             │  │   (analyze_heating_rate)         │ │
│  │                             │  │                                  │ │
│  │   Service Discovery:        │  │   - Calculate heating rate       │ │
│  │   bridge.sila2.local:8080   │  │   - Detect anomalies             │ │
│  │                             │  │   - Threshold: 3.0°C/min         │ │
│  │   10 MCP Tools:             │  └──────────────────────────────────┘ │
│  │   - list_devices            │                                        │
│  │   - get_device_info         │                                        │
│  │   - get_device_status       │                                        │
│  │   - set_temperature         │                                        │
│  │   - get_temperature         │                                        │
│  │   - subscribe_temperature   │                                        │
│  │   - get_heating_status      │                                        │
│  │   - abort_experiment        │                                        │
│  │   - get_task_status         │                                        │
│  │   - get_task_info           │                                        │
│  └─────────────────┬───────────┘                                        │
│                    │ gRPC (Port 50051)                                  │
│                    ↓                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │              Mock Device Container (ECS Fargate)                    ││
│  │                                                                     ││
│  │   Service Discovery: mock-devices.sila2.local:50051                ││
│  │                                                                     ││
│  │   HPLC Simulator:                                                  ││
│  │   - Temperature control (25-100°C)                                 ││
│  │   - Scenario switching (normal/slow heating)                       ││
│  │   - Scenario 1: 5°C/min (normal)                                   ││
│  │   - Scenario 2: 2°C/min (slow, triggers AI abort)                 ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Supporting Services                             │ │
│  │                                                                    │ │
│  │  • Amazon ECR: Container Registry                                 │ │
│  │    - sila2-bridge                                                  │ │
│  │    - sila2-mock-devices                                            │ │
│  │  • CloudWatch Logs: /ecs/sila2-* (7-day retention)                │ │
│  │  • VPC: Private Subnets (minimum 2)                                │ │
│  │  • Service Discovery: sila2.local namespace                        │ │
│  │  • Security Groups: Port 8080, 50051                               │ │
│  │  • IAM Roles: TaskExecutionRole, TaskRole                         │ │
│  │  • EventBridge Scheduler: Periodic analysis (5 min)               │ │
│  │  • SNS Topic: Event notifications                                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Communication Flow

### 1. User Request → Device Execution
```
User (Streamlit UI)
  │
  │ HTTP Request: "Set temperature to 80°C"
  ↓
AgentCore Runtime
  │
  │ Agent Orchestration (Claude 3.5 Sonnet v2)
  │ Analyzes request and selects appropriate tool
  ↓
AgentCore Gateway
  │
  │ Routes to Target 1 (MCP Bridge)
  │ MCP Protocol (HTTP)
  │ Tool: set_temperature
  ↓
MCP Bridge Container (bridge.sila2.local:8080)
  │
  │ FastAPI MCP Server
  │ Parse MCP request
  │ Validate tool schema
  ↓
SiLA2 Bridge Client
  │
  │ gRPC Call (Port 50051)
  │ Proto: sila2_basic.proto
  ↓
Mock Device Container (mock-devices.sila2.local:50051)
  │
  │ HPLC Simulator
  │ Execute temperature control
  │ Return task UUID
  ↓
[Response flows back through the same path]
```

### 2. Autonomous Analysis Flow
```
EventBridge Scheduler (every 5 minutes)
  │
  │ Trigger Lambda Invoker
  ↓
Lambda Invoker
  │
  │ 1. Get device status via AgentCore
  │ 2. Collect temperature history
  ↓
AgentCore Runtime
  │
  │ Agent analyzes situation
  │ Decides which tools to call
  ↓
AgentCore Gateway
  │
  ├─→ Target 1: get_temperature (MCP Bridge)
  │   └─→ Returns current temperature
  │
  └─→ Target 2: analyze_heating_rate (Lambda)
      └─→ Calculates rate, detects anomalies
  ↓
If anomaly detected (rate < 3.0°C/min):
  │
  │ Agent re-verifies:
  │ 1. Take first temperature measurement
  │ 2. Wait 5 seconds
  │ 3. Take second temperature measurement
  │ 4. Recalculate heating rate
  ↓
If still anomalous:
  │
  └─→ Target 1: abort_experiment (MCP Bridge)
      └─→ Stops heating, records to Memory
```

### 3. Service Discovery Flow
```
MCP Bridge Container
  │
  │ DNS Query: mock-devices.sila2.local
  ↓
AWS Cloud Map (Service Discovery)
  │
  │ Returns: Private IP of Mock Device Container
  ↓
MCP Bridge Container
  │
  │ gRPC Connection: <private-ip>:50051
  ↓
Mock Device Container
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          VPC                                 │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Private Subnet 1 (AZ-a)                    ││
│  │                                                          ││
│  │  ┌──────────────────┐      ┌──────────────────┐        ││
│  │  │  Bridge          │      │  Mock Devices    │        ││
│  │  │  ECS Task        │─────▶│  ECS Task        │        ││
│  │  │  (Fargate)       │ gRPC │  (Fargate)       │        ││
│  │  └──────────────────┘      └──────────────────┘        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Private Subnet 2 (AZ-b)                    ││
│  │                                                          ││
│  │  ┌──────────────────┐      ┌──────────────────┐        ││
│  │  │  Bridge          │      │  Mock Devices    │        ││
│  │  │  ECS Task        │─────▶│  ECS Task        │        ││
│  │  │  (Standby)       │ gRPC │  (Standby)       │        ││
│  │  └──────────────────┘      └──────────────────┘        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Service Discovery (sila2.local)             ││
│  │                                                          ││
│  │  bridge.sila2.local:8080 → Bridge Container IP          ││
│  │  mock-devices.sila2.local:50051 → Mock Device IP        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  Security Groups                         ││
│  │                                                          ││
│  │  Bridge SG:                                              ││
│  │    Inbound:  Port 8080 (MCP from Gateway)               ││
│  │    Outbound: Port 443 (HTTPS)                           ││
│  │              Port 50051 (gRPC to Mock Devices)          ││
│  │                                                          ││
│  │  Mock Device SG:                                         ││
│  │    Inbound:  Port 50051 (gRPC from Bridge)              ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### MCP Bridge Container (Target 1)
- **Base Image**: python:3.11-slim
- **Exposed Port**: 8080 (HTTP)
- **Service Discovery**: bridge.sila2.local:8080
- **CPU**: 256 (.25 vCPU)
- **Memory**: 512 MB
- **Health Check**: /health endpoint

**10 MCP Tools**:
1. **list_devices**: List all available lab devices
2. **get_device_info**: Get information about a specific device
3. **get_device_status**: Get current status of a device
4. **set_temperature**: Set target temperature (returns task UUID)
5. **get_temperature**: Get current temperature reading
6. **subscribe_temperature**: Subscribe to real-time temperature updates
7. **get_heating_status**: Get current heating status
8. **abort_experiment**: Abort current temperature control operation
9. **get_task_status**: Get status of an asynchronous task
10. **get_task_info**: Get information about a task

### Analysis Lambda (Target 2)
- **Function**: analyze_heating_rate
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds

**Functionality**:
- Calculate heating rate from temperature history
- Detect anomalies (threshold: 3.0°C/min)
- Return rate and anomaly status
- Used for both initial detection and re-verification

### Mock Device Container
- **Base Image**: python:3.11-slim
- **Exposed Port**: 50051 (gRPC)
- **Service Discovery**: mock-devices.sila2.local:50051
- **CPU**: 256 (.25 vCPU)
- **Memory**: 512 MB

**HPLC Simulator Features**:
- Temperature range: 25-100°C
- Scenario 1 (Normal): 5°C/min heating rate
- Scenario 2 (Slow): 2°C/min heating rate (triggers AI abort)
- Automatic scenario switching with each temperature setting
- Task-based asynchronous operations

### Lambda Invoker
- **Function**: sila2-agentcore-invoker
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 300 seconds (5 minutes)
- **VPC**: Enabled (requires VPC Endpoint for Bedrock)

**Functionality**:
- Triggered by EventBridge Scheduler (every 5 minutes)
- Invokes AgentCore Runtime for autonomous analysis
- Monitors device status and temperature history
- Publishes events to SNS topic

## Deployment Architecture

### ECS Fargate Tasks
- **Launch Type**: FARGATE
- **Network Mode**: awsvpc
- **Assign Public IP**: ENABLED (for ECR access)
- **Desired Count**: 1 per service

### Service Discovery
- **Namespace**: sila2.local (Private DNS)
- **Services**:
  - bridge.sila2.local:8080
  - mock-devices.sila2.local:50051
- **DNS TTL**: 60 seconds
- **Health Check**: Custom config with failure threshold 1

### IAM Roles
- **TaskExecutionRole**: ECR/CloudWatch access
- **TaskRole**: Lambda invocation, SNS publish permissions

### CloudWatch Logs
- **Bridge Logs**: /ecs/sila2-bridge-dev
- **Mock Device Logs**: /ecs/sila2-mock-devices-dev
- **Retention**: 7 days

## Data Flow Examples

### Example 1: Set Temperature
```
1. User: "Set temperature to 80°C"
2. AgentCore Runtime: Analyzes request
3. Gateway → Bridge: set_temperature(80)
4. Bridge → Mock Device: gRPC SetTemperature(80)
5. Mock Device: Returns task UUID
6. Bridge → Gateway: {"command_uuid": "abc-123", "status": "started"}
7. AgentCore → User: "Temperature set to 80°C, task ID: abc-123"
```

### Example 2: Autonomous Anomaly Detection
```
1. EventBridge: Triggers Lambda Invoker (every 5 min)
2. Invoker → AgentCore: "Analyze device status"
3. AgentCore → Bridge: get_temperature()
4. Bridge → Mock Device: gRPC GetTemperature()
5. Mock Device: Returns 35°C
6. AgentCore → Lambda: analyze_heating_rate(history)
7. Lambda: Calculates rate = 2.0°C/min (< 3.0 threshold)
8. Lambda → AgentCore: {"is_anomaly": true, "rate": 2.0}
9. AgentCore: Decides to re-verify
10. AgentCore → Bridge: get_temperature() [1st measurement]
11. Wait 5 seconds
12. AgentCore → Bridge: get_temperature() [2nd measurement]
13. AgentCore → Lambda: analyze_heating_rate(verified_history)
14. Lambda: Confirms rate = 2.0°C/min
15. AgentCore → Bridge: abort_experiment("Heating rate too slow")
16. Bridge → Mock Device: gRPC AbortExperiment()
17. AgentCore → Memory: Records entire decision process
18. Invoker → SNS: Publishes abort event
```

## Cost Structure

### Monthly Cost (24/7 operation)
- **ECS Fargate (2 tasks)**: ~$48/month
  - Bridge: CPU (0.25 vCPU) + Memory (0.5 GB) = $24/month
  - Mock Device: CPU (0.25 vCPU) + Memory (0.5 GB) = $24/month
- **Lambda Invoker**: ~$5/month (8,640 invocations/month)
- **Lambda Analysis**: ~$2/month (included in Invoker calls)
- **CloudWatch Logs**: ~$2/month
- **ECR**: ~$1/month
- **Service Discovery**: ~$1/month
- **EventBridge Scheduler**: ~$0.10/month

**Total**: Approximately $59/month

### Cost Optimization Options
- Stop ECS services when not in use: ~$10/month (Lambda + storage only)
- On-demand startup: Start ECS only when needed
- Reduce EventBridge frequency: Less frequent analysis

## Security

### Network Security
- **Private Subnets**: No direct internet access
- **Service Discovery**: Internal DNS resolution only
- **Security Groups**: Principle of least privilege
- **VPC Endpoints**: Bedrock AgentCore access without NAT Gateway

### IAM Security
- **TaskExecutionRole**: Minimal permissions for ECR/CloudWatch
- **TaskRole**: Scoped to specific Lambda functions and SNS topics
- **Lambda Role**: VPC execution, Bedrock invocation

### Container Security
- **ECR Image Scanning**: Enabled
- **Read-only Root Filesystem**: Recommended
- **Non-root User**: Implemented in Dockerfiles
- **Health Checks**: Automatic unhealthy task replacement

## Monitoring

### CloudWatch Metrics
- ECS Service CPU/Memory utilization
- ECS Task count and health status
- Lambda invocation count and duration
- Lambda error rate and throttles

### CloudWatch Logs
- Bridge Container: /ecs/sila2-bridge-dev
- Mock Device Container: /ecs/sila2-mock-devices-dev
- Lambda Invoker: /aws/lambda/sila2-agentcore-invoker
- Lambda Analysis: /aws/lambda/sila2-analyze-heating-rate

### Health Checks
- Bridge Container: /health endpoint (30-second interval)
- Service Discovery: Automatic DNS updates on task changes
- ECS Service: Automatic task replacement on failures

## Scalability

### Current Configuration
- **Bridge Service**: 1 task (can scale to N)
- **Mock Device Service**: 1 task (can scale to N)
- **Service Discovery**: Automatic load balancing across tasks

### Scaling Options
1. **Horizontal Scaling**: Increase DesiredCount in ECS Service
2. **Auto Scaling**: Configure based on CPU/Memory metrics
3. **Multi-Region**: Deploy in multiple AWS regions
4. **Edge Deployment**: Use AWS IoT Greengrass for on-premises devices

## Future Enhancements

### Phase 1: Production Readiness
- Add Application Load Balancer for external access
- Implement authentication and authorization
- Add request rate limiting
- Enhanced monitoring and alerting

### Phase 2: Real Device Integration
- Replace mock devices with real SiLA2 devices
- Implement device discovery protocol
- Add device health monitoring
- Support multiple device types

### Phase 3: Edge Deployment
- Deploy Bridge Container to AWS IoT Greengrass
- Support offline operation
- Local network optimization
- Sync with cloud for analytics

### Phase 4: Advanced Features
- Multi-agent collaboration
- Predictive maintenance
- Experiment workflow automation
- Integration with LIMS systems
