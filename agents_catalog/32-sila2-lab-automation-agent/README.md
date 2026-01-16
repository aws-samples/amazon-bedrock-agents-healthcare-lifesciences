# SiLA2 Lab Automation Agent

An AI-powered laboratory automation agent that controls SiLA2-compliant devices using Amazon Bedrock AgentCore. The agent autonomously monitors device status, analyzes experimental data, and makes intelligent control decisions.

## Overview

This agent demonstrates autonomous laboratory equipment control through:
- **AI-Driven Decision Making**: Claude 3.5 Sonnet v2 analyzes device data and makes control decisions
- **SiLA2 Protocol Integration**: Standard laboratory automation protocol support
- **Multi-Target Architecture**: Separates device control (Container) from data analysis (Lambda)
- **Memory Management**: Tracks experimental context and control history
- **Real-time Monitoring**: Streamlit UI for visualization and manual intervention

## Architecture

```
User/Lambda Invoker → AgentCore Runtime → MCP Gateway (2 Targets)
                                           ├─ Target 1: Bridge Container (5 tools)
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

## Getting Started

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

1. Clone this repository

```bash
git clone <repository-url>
cd 32-sila2-lab-automation-agent
```

2. Install Python dependencies

```bash
pip install -r requirements.txt
```

3. Configure AWS credentials

```bash
aws configure
export AWS_REGION=us-west-2
```

### VPC Requirements

The Lambda Invoker runs inside a VPC and requires a VPC Endpoint for Bedrock AgentCore API access:

```bash
# Create VPC Endpoint (recommended, ~$7/month)
./scripts/00_setup_vpc_endpoint.sh
```

Alternative: NAT Gateway (not recommended, ~$32/month)

## Deployment

1. Create ECR repositories and build container images

```bash
cd scripts
./01_setup_ecr_and_build.sh
```

2. Package Lambda functions

```bash
./02_package_lambdas.sh
```

3. Deploy main infrastructure stack

```bash
./03_deploy_stack.sh
```

4. Deploy AgentCore Runtime with Gateway and Memory

```bash
./04_deploy_agentcore.sh
```

For detailed deployment instructions, troubleshooting, and advanced configuration options, see [scripts/DEPLOYMENT_GUIDE.md](scripts/DEPLOYMENT_GUIDE.md).

## Available Tools

### Target 1: Bridge Container (5 tools)

- **list_devices()**: List all available SiLA2 devices
- **get_device_status(device_id)**: Get current device status
- **get_task_status(device_id, task_id)**: Check task execution status
- **get_property(device_id, property_name)**: Read device property values
- **execute_control(device_id, command, parameters)**: Execute control commands
  - `set_temperature`: Set target temperature
  - `abort_experiment`: Stop current experiment

### Target 2: Analysis Lambda (1 tool)

- **analyze_heating_rate(device_id, history)**: Calculate heating rate and detect anomalies

## Usage

### Manual Control

```bash
# Set device temperature
agentcore invoke '{"prompt": "Set HPLC_001 temperature to 80 degrees"}'

# Check device status
agentcore invoke '{"prompt": "What is the current status of HPLC_001?"}'
```

### Autonomous Analysis

The Lambda Invoker performs periodic analysis every 5 minutes:

```bash
# Trigger periodic analysis
aws lambda invoke \
  --function-name sila2-agentcore-invoker \
  --payload '{"action": "periodic", "devices": ["hplc_001"]}' \
  response.json

# View results
cat response.json
```

**Example Response:**
```json
{
  "analysis": {
    "heating_rate": 2.0,
    "expected_rate": 10.0,
    "is_anomaly": true,
    "scenario_mode": "scenario_2"
  },
  "decision": "Heating rate too slow, resetting temperature",
  "action_taken": "set_temperature",
  "reasoning": "Detected scenario_2, recovery to scenario_1 needed"
}
```

### Streamlit UI

Launch the monitoring interface:

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
   - AI anomaly detection reasoning
   - Automatic abort decisions when heating is too slow
   - Session and event tracking

**Scenario Switching:**
The system alternates between normal (5°C/min) and slow (2°C/min) heating scenarios with each temperature setting, demonstrating AI's ability to detect and respond to anomalies.

## Project Structure

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
├── main_agentcore.py            # AgentCore entrypoint
└── README.md
```

## Demo

### Streamlit UI Walkthrough

1. Start the Streamlit monitoring interface:

```bash
streamlit run streamlit_app/app.py
```

Your web browser should automatically launch and navigate to <http://localhost:8501>.

2. The UI displays three tabs:
   - **📊 Monitor**: Real-time temperature monitoring and status
   - **🎛️ Control**: Manual device control interface
   - **🧠 AI Memory**: AI decision history and reasoning

3. Test temperature control in the **🎛️ Control** tab:

   a. Set target temperature to 35°C
   - Temperature will gradually increase from 25°C to 35°C
   - Monitor the temperature rise in the **📊 Monitor** tab

   b. When temperature reaches 35°C:
   - Heating automatically stops
   - Check the **🧠 AI Memory** tab to see "Temperature target reached" notification

4. Observe AI autonomous control:

   The system alternates between two scenarios with each temperature setting:
   
   - **Normal heating (Scenario 1)**: Temperature rises at 5°C/min
   - **Slow heating (Scenario 2)**: Temperature rises at 2°C/min (abnormally slow)

   When slow heating is detected:
   - AI automatically detects the anomaly
   - AI aborts the experiment to prevent issues
   - Check the **🧠 AI Memory** tab to see AI's reasoning: "Heating rate too slow, aborting experiment"

5. Repeat temperature settings to see scenario switching:
   - 1st setting: Normal heating (5°C/min) → reaches target
   - 2nd setting: Slow heating (2°C/min) → AI aborts
   - 3rd setting: Normal heating (5°C/min) → reaches target
   - And so on...

### Command Line Testing

Alternatively, test using command line:

```bash
# Set device temperature
agentcore invoke '{"prompt": "Set HPLC_001 temperature to 35 degrees"}'

# Check device status
agentcore invoke '{"prompt": "What is the current status of HPLC_001?"}'

# Trigger autonomous analysis
aws lambda invoke \
  --function-name sila2-agentcore-invoker \
  --payload '{"action": "periodic", "devices": ["hplc_001"]}' \
  response.json

cat response.json
```

## Clean up

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

## Troubleshooting

### Common Issues

**Issue**: Lambda Invoker cannot reach Bedrock AgentCore API
- **Solution**: Ensure VPC Endpoint is created or NAT Gateway is configured

**Issue**: Container fails to start in ECS
- **Solution**: Check ECR image exists and ECS task role has proper permissions

**Issue**: AgentCore deployment fails
- **Solution**: Verify IAM role has `bedrock-agentcore:*` permissions

See [docs/troubleshooting.md](docs/troubleshooting.md) for detailed troubleshooting guide.

## Architecture Details

For detailed architecture documentation, see:
- [docs/architecture.md](docs/architecture.md) - System architecture overview
- [docs/deployment.md](docs/deployment.md) - Deployment architecture
- [docs/development.md](docs/development.md) - Development guide

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with clear commit messages
4. Test your changes thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT-0 License - see the LICENSE file for details.

## Acknowledgments

- Built with [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
- Uses [SiLA2 Standard](https://sila-standard.com/) for laboratory automation
- Powered by Anthropic Claude 3.5 Sonnet v2
