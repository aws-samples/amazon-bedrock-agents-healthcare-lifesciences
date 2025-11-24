# SiLA2 Lab Automation Agent

**Phase 2 Complete** ✅ - Amazon Bedrock AgentCore + Gateway integration for laboratory automation using SiLA2 protocols.

## 🚀 Quick Deploy

```bash
# Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Deploy everything (Phase 2 - Gateway Integration)
./deploy-corrected.sh

# Test AgentCore integration
agentcore status
agentcore invoke '{"prompt": "List all available SiLA2 devices"}'

# Test Streamlit UI
streamlit run streamlit_app_agentcore.py
```

## 🏗️ Architecture (Phase 2)

```
User → AgentCore Runtime → Gateway API → Lambda → SiLA2 Tools → Lab Devices
```

- **Framework**: Amazon Bedrock AgentCore + Strands Agents SDK
- **Model**: Anthropic Claude 3.5 Sonnet v2
- **Gateway**: AWS Lambda + API Gateway + MCP Gateway
- **Infrastructure**: CloudFormation (ECR + IAM + Lambda + API Gateway)
- **Runtime**: Docker ARM64 on AWS CodeBuild
- **UI**: Streamlit with AgentCore integration

## 🔧 Available SiLA2 Tools

- `list_available_devices()`: List all laboratory devices
- `get_device_status(device_name)`: Check specific device status
- `execute_device_command(device_name, command)`: Execute device commands
- `get_device_capabilities(device_name)`: Get device capabilities
- `start_measurement(device_name, parameters)`: Start measurements
- `stop_measurement(device_name)`: Stop ongoing measurements

## 📁 Key Files (Phase 2)

- `deploy-corrected.sh` - **Main deployment script** ✅
- `main_aws_official_final.py` - AgentCore Runtime implementation ✅
- `gateway/sila2_gateway_mcp_tools.py` - Gateway Lambda handler ✅
- `infrastructure/sila2-agent-simple-fixed.yaml` - CloudFormation template ✅
- `streamlit_app_agentcore.py` - Streamlit UI with AgentCore integration ✅
- `.bedrock_agentcore.yaml` - AgentCore configuration ✅

## 🎯 Phase 2 Achievements

- ✅ **AWS Official Pattern**: BedrockAgentCoreApp + @app.entrypoint
- ✅ **Gateway Integration**: MCP Gateway + Target configuration
- ✅ **Strands SDK Integration**: Proper tool execution via Gateway API
- ✅ **Input Processing**: Dictionary format input handling
- ✅ **ARM64 Deployment**: CodeBuild-based container deployment
- ✅ **Streamlit UI**: Interactive interface with AgentCore integration
- ✅ **End-to-End Testing**: Confirmed working AgentCore invoke

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

## 🔄 Next Steps (Phase 3)

- Real SiLA2 protocol implementation
- Actual device communication
- Enhanced error handling
- Production-ready optimizations

See `DEVELOPMENT_PLAN.md` for detailed roadmap and `AWS_DEPLOYMENT_GUIDE.md` for advanced deployment options.