# Phase 3 Deployment Order

## 📋 Optimized Deployment Sequence

### 01. setup_infrastructure.sh
**Purpose:** CloudFormation stack + IAM roles
- Creates base infrastructure
- Sets up Lambda execution roles
- Prepares ECR repositories

### 02. deploy_mock_devices.sh
**Purpose:** Mock SiLA2 device Lambdas
- Creates gRPC layer
- Deploys HPLC, Centrifuge, Pipette mock devices
- Python 3.10 runtime with SiLA2 compliance

### 03. setup_mcp_bridge.sh
**Purpose:** MCP-gRPC Bridge Lambda
- Creates bridge Lambda function
- Enables device communication routing
- API Gateway Proxy support

### 04. create_device_gateway.sh
**Purpose:** Device API Gateway
- Creates REST API Gateway
- Configures endpoints (/devices, /devices/{id}, /execute)
- Links to MCP Bridge Lambda

### 05. create_gateway.sh
**Purpose:** MCP Gateway Creation
- Creates MCP Gateway via agentcore CLI
- Sets up IAM permissions
- Saves gateway configuration

### 06. create_gateway_target.sh
**Purpose:** Gateway Target Creation
- Creates Gateway Target using boto3
- Links Lambda (mcp_grpc_bridge_lambda_gateway.py) to Gateway
- Configures tool schema for SiLA2 devices
- Adds Lambda permissions

### 07. deploy_agentcore.sh
**Purpose:** AgentCore Runtime Deployment
- Configures .bedrock_agentcore.yaml
- Deploys AgentCore runtime container
- Tests agent invocation

### 08. integrate_phase3.sh
**Purpose:** Integration testing
- Tests mock devices
- Tests MCP bridge
- Tests API Gateway
- End-to-end validation

### 09. setup_ui.sh
**Purpose:** Streamlit UI
- Deploys user interface
- Connects to AgentCore runtime

### 10. run_tests.sh
**Purpose:** Final validation
- Comprehensive test suite
- Performance validation

## 🔄 Dependency Flow

```
01 (Infrastructure)
  ↓
02 (Mock Devices) ←─┐
  ↓                 │
03 (MCP Bridge) ←───┤ Lambda functions must exist
  ↓                 │
04 (API Gateway) ←──┘
  ↓
05 (Create Gateway) ← Requires execution role
  ↓
06 (Create Gateway Target) ← Requires Gateway ARN + Lambda ARN
  ↓
07 (Deploy AgentCore Runtime) ← Requires Gateway config
  ↓
08 (Integration Tests)
  ↓
09 (UI)
  ↓
10 (Final Tests)
```

## ⚠️ Key Points

1. **Lambda Implementation:** Uses Gateway Lambda Target format (context.client_context)
2. **Tool Schema:** Defined in Gateway Target, not in Lambda code
3. **Deployment Order:** Lambda functions (02-04) before Gateway (05-06)

## 🚀 Quick Deploy

```bash
cd scripts
./deploy_all.sh  # Automated 10-step deployment
```

Or step-by-step:
```bash
./01_setup_infrastructure.sh    # CloudFormation + IAM
./02_deploy_mock_devices.sh     # Mock device Lambdas
./03_setup_mcp_bridge.sh        # MCP Bridge (Gateway format)
./04_create_device_gateway.sh   # API Gateway
./05_create_gateway.sh          # MCP Gateway
./06_create_gateway_target.sh   # Gateway Target
./07_deploy_agentcore.sh        # AgentCore Runtime
./08_integrate_phase3.sh        # Integration tests
./09_setup_ui.sh                # Streamlit UI
./10_run_tests.sh               # Final validation
```
