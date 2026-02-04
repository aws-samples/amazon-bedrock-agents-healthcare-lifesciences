# SiLA2 Lab Automation Agent

An AI-powered laboratory automation agent that controls SiLA2-compliant devices using Amazon Bedrock AgentCore. The agent autonomously monitors device status, analyzes experimental data, and makes intelligent control decisions.

## 🌟 Overview

This agent demonstrates autonomous laboratory equipment control through:
- **AI-Driven Decision Making**: Claude 3.5 Sonnet v2 analyzes device data and makes control decisions
- **SiLA2 Protocol Integration**: Standard laboratory automation protocol support
- **Multi-Target Architecture**: Separates device control (Container) from data analysis (Lambda)
- **Memory Management**: Tracks experimental context and control history with automatic audit trail
- **Real-time Monitoring**: Streamlit UI for visualization and manual intervention
- **Intelligent Verification**: Re-confirms anomalies before taking critical actions

## 🏗️ Architecture

```
User/Lambda Invoker → AgentCore Runtime → MCP Gateway (2 Targets)
                                           ├─ Target 1: Bridge Container (10 tools)
                                           │   └─ Mock Devices (ECS)
                                           └─ Target 2: Lambda (1 tool)
```

**Key Components:**
- **AgentCore Runtime**: AI agent orchestration with Claude 3.5 Sonnet v2
- **MCP Gateway**: Multi-target tool routing (Container + Lambda)
- **Bridge Container**: SiLA2 protocol translation (ECS Fargate)
- **Mock Devices**: HPLC simulator with scenario switching
- **Analysis Lambda**: Temperature rate calculation and anomaly detection
- **Streamlit UI**: Real-time monitoring and manual control interface

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

## 🔄 SiLA2 to MCP Protocol Translation

This agent bridges SiLA2 (Standard in Lab Automation) and MCP (Model Context Protocol) to enable AI-driven laboratory automation.

**Key Translation Mechanisms:**

1. **Command/Property-to-Tool Mapping (1:1)**: Each SiLA2 Command or Property maps to one MCP tool
   - Commands: `SetTemperature` → `set_temperature`, `AbortExperiment` → `abort_experiment`
   - Properties: `CurrentTemperature` → `get_temperature`, `HeatingStatus` → `get_heating_status`

2. **Protocol Conversion**: Bridge Container translates between gRPC (SiLA2) and HTTP/JSON (MCP)
   ```
   AI Agent (MCP/JSON) ←→ Bridge Container ←→ SiLA2 Devices (gRPC)
   ```

3. **Command Type Handling**:
   - **Observable Commands**: Returns task UUID, monitors progress asynchronously
   - **Unobservable Commands**: Returns result immediately
   - **Properties**: Get/Subscribe to real-time values

For implementation details, see `src/bridge/` directory and [ARCHITECTURE.md](ARCHITECTURE.md).

## ✨ Key Features

### Intelligent Heating Rate Verification

When periodic monitoring detects a potentially slow heating rate, the agent:

1. **Re-measures temperature** using SiLA2 standard tools (5-second interval)
2. **Re-calculates heating rate** with fresh data
3. **Makes informed decision** based on verified measurements
4. **Records entire process** to Memory for audit trail

This prevents false positives and ensures reliable anomaly detection.

### Automatic Memory Recording

All agent activities are automatically recorded to AgentCore Memory:
- Tool calls and results
- Temperature measurements and timestamps
- Heating rate calculations
- Control decisions and reasoning
- Experiment abort events

Memory provides complete audit trail for regulatory compliance and troubleshooting.

## 🚀 Getting Started

### Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+
- Docker (for local testing and AgentCore deployment)
- AWS Account with access to:
  - Amazon Bedrock AgentCore
  - AWS Lambda
  - Amazon ECR
  - Amazon ECS Fargate
  - Amazon VPC (with VPC Endpoints)
  - AWS CloudFormation

### Installation

1. **Clone this repository**

```bash
git clone <repository-url>
cd agents_catalog/32-sila2-lab-automation-agent
```

2. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure AWS credentials**

```bash
aws configure
export AWS_REGION=us-west-2
```

### VPC Requirements

The Lambda Invoker runs inside a VPC and requires VPC Endpoints for AWS service access. The deployment script automatically creates the following VPC Endpoints:

- **Bedrock AgentCore**: For AI agent invocation
- **ECR API/DKR**: For container image pulls
- **CloudWatch Logs**: For logging
- **S3 Gateway**: For artifact storage
- **SNS**: For event notifications

**Cost**: ~$7/month per Interface VPC Endpoint (5 endpoints = ~$35/month)

## 📦 Deployment

### Quick Start

```bash
cd scripts

# 1. Create ECR repositories and build container images
./01_setup_ecr_and_build.sh

# 2. Package Lambda functions
./02_package_lambdas.sh

# 3. Deploy main infrastructure stack
./03_deploy_stack.sh \
  --vpc-id <your-vpc-id> \
  --subnet-ids <subnet-id-1>,<subnet-id-2>

# 4. Deploy AgentCore Runtime with Gateway and Memory
./04_deploy_agentcore.sh
```

### Detailed Deployment Steps

#### Step 1: Setup ECR and Build Images

```bash
./scripts/01_setup_ecr_and_build.sh
```

This script:
- Creates ECR repositories for bridge and mock-devices containers
- Builds Docker images
- Pushes images to ECR

#### Step 2: Package Lambda Functions

```bash
./scripts/02_package_lambdas.sh
```

This script:
- Packages Lambda Invoker function
- Packages Analysis Lambda function
- Creates zip files in `build/` directory

#### Step 3: Deploy Infrastructure

```bash
./scripts/03_deploy_stack.sh \
  --vpc-id vpc-xxxxx \
  --subnet-ids subnet-xxxxx,subnet-yyyyy
```

**Required Parameters:**
- `--vpc-id`: Your VPC ID
- `--subnet-ids`: Comma-separated list of private subnet IDs (minimum 2)

**Optional Parameters:**
- `--route-table-ids`: Comma-separated route table IDs (auto-detected if not provided)

This script deploys:
- VPC Endpoints (Bedrock AgentCore, ECR, CloudWatch Logs, S3, SNS)
- ECS Cluster with Bridge and Mock Device containers
- Lambda functions (Invoker and Analysis)
- Service Discovery (sila2.local namespace)
- Security Groups
- EventBridge Scheduler (5-minute periodic analysis)
- SNS Topic for events

#### Step 4: Deploy AgentCore

```bash
./scripts/04_deploy_agentcore.sh
```

This script:
- Creates AgentCore Runtime
- Configures Gateway with 2 targets
- Sets up Memory for audit trail
- Deploys Runtime container to ECS

## 🛠️ Available Tools

### Target 1: Bridge Container (10 tools)

1. **list_devices()**: List all available lab devices
2. **get_device_info(device_id)**: Get information about a specific device
3. **get_device_status(device_id)**: Get current status of a device
4. **set_temperature(target_temperature)**: Set target temperature (returns task UUID)
5. **get_temperature()**: Get current temperature reading
6. **subscribe_temperature()**: Subscribe to real-time temperature updates
7. **get_heating_status()**: Get current heating status
8. **abort_experiment(reason)**: Abort current temperature control operation
9. **get_task_status(task_id)**: Get status of an asynchronous task
10. **get_task_info(task_id)**: Get information about a task

### Target 2: Analysis Lambda (1 tool)

- **analyze_heating_rate(device_id, history)**: Calculate heating rate and detect anomalies
  - Used for both initial detection and re-verification
  - Ensures consistent calculation logic
  - Returns rate in °C/min with threshold comparison (3.0°C/min)

## 💻 Usage

### Streamlit UI

First, install the required dependencies:

```bash
pip install -r streamlit_app/requirements.txt
```

Then launch the monitoring interface:

```bash
streamlit run streamlit_app/app.py
```

Your web browser should automatically launch and navigate to <http://localhost:8501>.

**Three-Tab Interface:**

1. **📊 Monitor**: Real-time device monitoring
   - Temperature graph with real-time updates
   - Current temperature, target, and elapsed time
   - Heating rate calculation (5°C/min normal, 2°C/min slow)
   - Scenario indicator (Scenario 1 or Scenario 2)

2. **🎛️ Control**: Manual device control
   - Set target temperature (25-100°C)
   - Send custom commands to AI agent
   - View AI responses and reasoning

3. **🧠 AI Memory**: AI decision history
   - Temperature target reached notifications
   - AI anomaly detection reasoning with verification steps
   - Automatic abort decisions when heating is too slow
   - Complete audit trail with timestamps
   - Tool call history and results
   - Session and event tracking

**Scenario Switching:**
The system alternates between normal (5°C/min) and slow (2°C/min) heating scenarios with each temperature setting, demonstrating AI's ability to detect and respond to anomalies.

### Manual Control via CLI

```bash
# Set device temperature
aws bedrock-agentcore-runtime invoke-agent \
  --agent-id <agent-id> \
  --agent-alias-id <alias-id> \
  --session-id test-session \
  --input-text "Set temperature to 80 degrees" \
  --region us-west-2

# Check device status
aws bedrock-agentcore-runtime invoke-agent \
  --agent-id <agent-id> \
  --agent-alias-id <alias-id> \
  --session-id test-session \
  --input-text "What is the current status of the device?" \
  --region us-west-2
```

### Autonomous Analysis with Intelligent Verification

The Lambda Invoker performs periodic analysis every 5 minutes. When a potential anomaly is detected, the agent automatically performs intelligent verification:

**Verification Protocol:**
1. Receive heating rate alert from periodic monitoring
2. Take first temperature measurement
3. Wait 5 seconds
4. Take second temperature measurement
5. Calculate heating rate from verified measurements
6. Make abort decision if rate < 3.0°C/min
7. Record entire process to Memory

```bash
# Trigger periodic analysis manually
aws lambda invoke \
  --function-name sila2-agentcore-invoker \
  --payload '{"action": "periodic", "device_id": "hplc"}' \
  response.json

# View results
cat response.json
```

## 🎬 Demo Walkthrough

### Streamlit UI Demo

1. **Install Streamlit dependencies:**

```bash
pip install -r streamlit_app/requirements.txt
```

2. **Start the Streamlit monitoring interface:**

```bash
streamlit run streamlit_app/app.py
```

Your web browser should automatically launch and navigate to <http://localhost:8501>.

3. **The UI displays three tabs:**
   - **📊 Monitor**: Real-time temperature monitoring and status
   - **🎛️ Control**: Manual device control interface
   - **🧠 AI Memory**: AI decision history and reasoning

4. **Test temperature control in the 🎛️ Control tab:**

   a. Set target temperature to 35°C
   - Temperature will gradually increase from 25°C to 35°C
   - Monitor the temperature rise in the **📊 Monitor** tab

   b. When temperature reaches 35°C:
   - Heating automatically stops
   - Check the **🧠 AI Memory** tab to see "Temperature target reached" notification

5. **Observe AI autonomous control:**

   The system alternates between two scenarios with each temperature setting:
   
   - **Normal heating (Scenario 1)**: Temperature rises at 5°C/min
   - **Slow heating (Scenario 2)**: Temperature rises at 2°C/min (abnormally slow)

   When slow heating is detected:
   - AI automatically detects the anomaly
   - AI aborts the experiment to prevent issues
   - Check the **🧠 AI Memory** tab to see AI's reasoning: "Heating rate too slow, aborting experiment"

5. **Repeat temperature settings to see scenario switching:**
   - 1st setting: Normal heating (5°C/min) → reaches target
   - 2nd setting: Slow heating (2°C/min) → AI aborts
   - 3rd setting: Normal heating (5°C/min) → reaches target
   - And so on...

## 📁 Project Structure

```
32-sila2-lab-automation-agent/
├── agentcore/                    # AgentCore configuration
│   ├── agent_instructions.txt   # AI agent instructions
│   ├── gateway_config.py        # Gateway setup
│   └── runtime_config.py        # Runtime configuration
├── infrastructure/               # CloudFormation templates
│   ├── main.yaml                # Main stack
│   ├── gateway.yaml             # AgentCore Gateway
│   └── nested/                  # Nested stacks (ECS, Lambda, Network)
├── scripts/                      # Deployment scripts
│   ├── 01_setup_ecr_and_build.sh
│   ├── 02_package_lambdas.sh
│   ├── 03_deploy_stack.sh
│   ├── 04_deploy_agentcore.sh
│   └── destroy.sh
├── src/                          # Application source code
│   ├── bridge/                  # MCP Bridge container
│   ├── devices/                 # Mock device simulators
│   └── lambda/                  # Lambda functions
├── streamlit_app/               # Monitoring UI
├── ARCHITECTURE.md              # Detailed architecture documentation
├── main_agentcore.py            # AgentCore entrypoint
└── README.md
```

## 🧹 Clean Up

To destroy all deployed resources, run:

```bash
cd scripts
./destroy.sh
```

This will delete:
- AgentCore Runtime and Gateway
- CloudFormation stacks
- ECR repositories
- Lambda functions
- ECS services

## 🔧 Troubleshooting

### Common Issues

**Issue**: Lambda Invoker cannot reach Bedrock AgentCore API
- **Solution**: VPC Endpoints are automatically created by the deployment script
- **Check**: Verify VPC Endpoints exist in EC2 Console → Endpoints
- **Verify**: `com.amazonaws.<region>.bedrock-agentcore` endpoint is active

**Issue**: Container fails to start in ECS
- **Solution**: Check ECR image exists and ECS task role has proper permissions
- **Check logs**: CloudWatch Logs `/ecs/sila2-bridge-dev` and `/ecs/sila2-mock-devices-dev`

**Issue**: AgentCore deployment fails
- **Solution**: Verify IAM role has `bedrock-agentcore:*` permissions
- **Check**: Ensure Docker is running for local builds

**Issue**: Service Discovery not resolving
- **Solution**: Verify ECS tasks are running and registered with Service Discovery
- **Check**: `bridge.sila2.local:8080` and `mock-devices.sila2.local:50051` DNS resolution

**Issue**: EventBridge Scheduler not triggering
- **Solution**: Check EventBridge Scheduler is enabled and Lambda has proper permissions
- **Check**: CloudWatch Logs `/aws/lambda/sila2-agentcore-invoker`

For detailed troubleshooting, see the Troubleshooting section above.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with clear commit messages
4. Test your changes thoroughly
5. Submit a pull request

## ⚠️ Security Considerations for Production Use

**This is a prototype/sample implementation for demonstration and learning purposes.**

Before deploying to production environments, please address the following security considerations:

### IAM Permissions
- **Current**: Uses wildcard (`*`) resources for demo flexibility
- **Production**: Replace with specific ARNs for all IAM policies
- **Example**: `arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:agent/*`

### Network Security
- **Security Groups**: Egress rules default to allow-all for demo simplicity
  - **Production**: Restrict egress to specific destinations and ports
  - Add descriptions to all security group rules
- **VPC Configuration**: Review and minimize network exposure

### Input Validation
- **Current**: Sample code demonstrates core functionality without extensive validation
- **Production**: Implement comprehensive input validation and sanitization for:
  - Device IDs and task IDs
  - Temperature values and parameters
  - All user-provided inputs

### Encryption
- **CloudWatch Logs**: Consider enabling KMS encryption
- **SNS Topics**: Configure KMS encryption for sensitive notifications
- **ECR Repositories**: Enable KMS encryption and image scanning

### Lambda Configuration
- **Concurrency**: Set reserved concurrent executions to prevent resource exhaustion
- **Dead Letter Queue**: Configure DLQ for failed invocations
- **VPC Deployment**: Evaluate if Lambda functions should run inside VPC

### Dependency Management
- **Current**: Uses version ranges for flexibility (e.g., `>=2.31.0,<3.0.0`)
- **Production**: Pin to specific tested versions and regularly update for security patches
- **Scanning**: Implement automated dependency vulnerability scanning

### Monitoring and Auditing
- Enable AWS CloudTrail for all API calls
- Configure CloudWatch alarms for anomalous behavior
- Review and export AgentCore Memory logs regularly

### Compliance
This sample code is provided "as-is" for educational purposes. Ensure compliance with your organization's security policies and regulatory requirements before production use.

## 📄 License

This project is licensed under the MIT-0 License - see the [LICENSE](../../LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
- Uses [SiLA2 Standard](https://sila-standard.com/) for laboratory automation
- Powered by Anthropic Claude 3.5 Sonnet v2

## 📚 Additional Resources

- [Detailed Architecture Documentation](ARCHITECTURE.md)
