# SiLA2 Lab Automation Agent

**Phase 3 Complete** ✅ - Amazon Bedrock AgentCore + Gateway Lambda Target integration for laboratory automation using SiLA2 protocols.

## 🚀 Quick Deploy

```bash
# Deploy everything
cd scripts
./deploy_all.sh

# Test AgentCore
agentcore invoke "List all available SiLA2 devices"

# Launch UI
streamlit run streamlit_app_agentcore.py
```

## 🏗️ Architecture (Phase 3)

```
User → AgentCore Runtime → MCP Gateway → Gateway Target → Lambda (Gateway format) → Mock Devices
```

- **Framework**: Amazon Bedrock AgentCore
- **Model**: Anthropic Claude 3.5 Sonnet v2
- **Gateway**: MCP Gateway + Lambda Target (context.client_context)
- **Infrastructure**: CloudFormation (IAM + Lambda)
- **Mock Devices**: HPLC, Centrifuge, Pipette (Lambda functions)
- **UI**: Streamlit

## 🔧 Available SiLA2 Tools

- `list_available_devices()`: List all laboratory devices
- `get_device_status(device_name)`: Check specific device status
- `execute_device_command(device_name, command)`: Execute device commands
- `get_device_capabilities(device_name)`: Get device capabilities
- `start_measurement(device_name, parameters)`: Start measurements
- `stop_measurement(device_name)`: Stop ongoing measurements

## 📁 Key Files (Phase 3)

- `scripts/deploy_all.sh` - Automated 10-step deployment ✅
- `mcp_grpc_bridge_lambda_gateway.py` - Gateway Lambda Target implementation ✅
- `scripts/03_setup_mcp_bridge.sh` - Lambda deployment ✅
- `scripts/06_create_gateway_target.sh` - Gateway Target creation ✅
- `.bedrock_agentcore.yaml` - AgentCore configuration ✅
- `streamlit_app_agentcore.py` - Streamlit UI ✅

## 🎯 Phase 3 Achievements

- ✅ **Gateway Lambda Target**: Correct context.client_context implementation
- ✅ **Tool Schema Separation**: Schema in Gateway Target, logic in Lambda
- ✅ **Mock Device Integration**: HPLC, Centrifuge, Pipette Lambda functions
- ✅ **10-Step Deployment**: Automated infrastructure setup
- ✅ **AgentCore Integration**: End-to-end working pipeline
- ✅ **Streamlit UI**: Interactive device control interface

## 🧪 Example Usage

```bash
# List all devices
agentcore invoke '{"prompt": "List all available SiLA2 devices"}'

# Check specific device
agentcore invoke '{"prompt": "What is the status of HPLC-01?"}'

# Execute device command
agentcore invoke '{"prompt": "Start a measurement on PIPETTE-01"}'
```

**Expected Response**:
```
There are three SiLA2 devices currently available in the laboratory:
1. An HPLC system (HPLC-01) which is ready for use
2. A Centrifuge (CENTRIFUGE-01) which is currently busy  
3. A Pipette (PIPETTE-01) which is ready for use
```

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+
- Docker (for AgentCore Runtime)
- Required AWS services access:
  - Amazon Bedrock
  - AWS Lambda
  - Amazon ECR
  - AWS CodeBuild
  - Amazon API Gateway
  - AWS CloudFormation

## 🔄 Next Steps

- Real SiLA2 gRPC protocol implementation
- Physical device integration
- Production deployment optimization
- Advanced error handling and monitoring

See `scripts/DEPLOYMENT_ORDER.md` for deployment details.