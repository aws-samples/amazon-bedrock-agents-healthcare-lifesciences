# SiLA2 Lab Automation Agent

**Phase 4 Complete** ✅ - Amazon Bedrock AgentCore + MCP Gateway + ECS Fargate integration for laboratory automation using SiLA2 protocols.

## 🚀 Quick Deploy

```bash
# Deploy step by step
cd scripts
export AWS_REGION=us-west-2

./01_setup_infrastructure.sh  # Create ECR repositories
./02_build_containers.sh      # Build and push Docker containers
./03_deploy_ecs.sh           # Deploy ECS + Lambda Proxy
./04_create_gateway.sh       # Create MCP Gateway
./05_create_mcp_target.sh    # Create MCP Target
./06_deploy_agentcore.sh     # Deploy AgentCore Runtime
./07_run_tests.sh            # Run integration tests
./08_setup_ui.sh             # Setup Streamlit UI

# Test AgentCore
agentcore invoke "List all available SiLA2 devices"

# Launch UI
./run_streamlit.sh
```

## 🏗️ Architecture (Phase 4)

```
User → AgentCore Runtime → MCP Gateway → Lambda Proxy → ECS Bridge → Mock Devices (Container)
```

- **Framework**: Amazon Bedrock AgentCore
- **Model**: Anthropic Claude 3.5 Sonnet v2
- **Gateway**: MCP Gateway + Lambda Target
- **Infrastructure**: ECS Fargate + Lambda Proxy + CloudFormation
- **Mock Devices**: HPLC, Centrifuge, Pipette (ECS Container)
- **UI**: Streamlit (Local)

## 🔧 Available SiLA2 Tools

- `list_available_devices()`: List all laboratory devices
- `get_device_status(device_name)`: Check specific device status
- `execute_device_command(device_name, command)`: Execute device commands
- `get_device_capabilities(device_name)`: Get device capabilities
- `start_measurement(device_name, parameters)`: Start measurements
- `stop_measurement(device_name)`: Stop ongoing measurements

## 📁 Key Files (Phase 4)

### Deployment Scripts
- `scripts/01_setup_infrastructure.sh` - Create ECR repositories
- `scripts/02_build_containers.sh` - Build and push Docker containers
- `scripts/03_deploy_ecs.sh` - Deploy ECS + Lambda Proxy stacks
- `scripts/04_create_gateway.sh` - Create MCP Gateway
- `scripts/05_create_mcp_target.sh` - Create Lambda MCP Target
- `scripts/06_deploy_agentcore.sh` - Deploy AgentCore Runtime
- `scripts/07_run_tests.sh` - Run integration tests
- `scripts/08_setup_ui.sh` - Setup Streamlit UI

### Infrastructure
- `infrastructure/bridge_container_ecs_no_alb.yaml` - ECS Fargate stack
- `infrastructure/lambda_proxy.yaml` - Lambda Proxy stack
- `lambda_proxy/index.py` - Lambda Proxy implementation
- `bridge_container/main.py` - MCP Bridge container
- `mock_devices_container/server.py` - Mock devices gRPC server

### Application
- `main_agentcore_phase3.py` - AgentCore agent definition
- `.bedrock_agentcore.yaml` - AgentCore configuration
- `streamlit_mcp_tools.py` - Streamlit UI
- `test_phase4_integration.py` - Integration tests

## 🎯 Phase 4 Achievements

- ✅ **ECS Fargate Architecture**: Container-based deployment for scalability
- ✅ **Lambda Proxy**: VPC-enabled Lambda for ECS Bridge communication
- ✅ **MCP Gateway + Target**: Bedrock AgentCore Gateway integration
- ✅ **Service Discovery**: ECS Service Discovery for internal communication
- ✅ **Mock Device Container**: HPLC, Centrifuge, Pipette in single container
- ✅ **8-Step Deployment**: Modular infrastructure setup
- ✅ **AgentCore Integration**: End-to-end working pipeline
- ✅ **Integration Tests**: Automated testing with agentcore invoke
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

### Additional Prerequisites for Local Streamlit UI

To run the Streamlit UI locally, your AWS credentials must have the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "bedrock-agentcore:InvokeAgent",
      "bedrock-agentcore:InvokeAgentStream"
    ],
    "Resource": "*"
  }]
}
```

Add this policy to your IAM user/role:

```bash
aws iam put-role-policy --role-name YOUR_ROLE_NAME --policy-name BedrockAgentCoreInvokePolicy --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["bedrock-agentcore:InvokeAgent","bedrock-agentcore:InvokeAgentStream"],"Resource":"*"}]}'
```

## 🔄 Next Steps

- Real SiLA2 gRPC protocol implementation
- Physical device integration
- Production deployment optimization
- Advanced error handling and monitoring
- Auto-scaling configuration for ECS tasks

## 📚 Documentation

See `DEPLOYMENT_VALIDATION.md` for deployment troubleshooting and validation details.