# AgentCore Strands Template

> [!IMPORTANT]
> The examples provided in this repository are for experimental and educational purposes only. They demonstrate concepts and techniques but are not intended for direct use in production environments.

This is a template for creating AI agents using Amazon Bedrock AgentCore framework with Strands. The template provides a foundation for building agents that can connect to your own data infrastructure with your own local tools, includes a sample public tools gateway, Cognito authentication, memory capabilities, and a local Streamlit UI.

## Table of Contents

- [AgentCore Strands Template](#agentcore-strands-template)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
    - [AWS Account Setup](#aws-account-setup)
  - [Deploy](#deploy)
  - [Sample Queries](#sample-queries)
  - [Scripts](#scripts)
    - [Amazon Bedrock AgentCore Gateway](#amazon-bedrock-agentcore-gateway)
    - [Amazon Bedrock AgentCore Memory](#amazon-bedrock-agentcore-memory)
    - [Cognito Credentials Provider](#cognito-credentials-provider)
    - [Agent Runtime](#agent-runtime)
  - [Cleanup](#cleanup)
  - [🤝 Contributing](#-contributing)
  - [📄 License](#-license)

## Prerequisites

### AWS Account Setup

1. **AWS Account**: You need an active AWS account with appropriate permissions
   - [Create AWS Account](https://aws.amazon.com/account/)
   - [AWS Console Access](https://aws.amazon.com/console/)

2. **AWS Command Line Interface (AWS CLI)**: Install and configure AWS Command Line Interface (AWS CLI) with your credentials
   - [Install AWS Command Line Interface (AWS CLI)](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
   - [Configure AWS Command Line Interface (AWS CLI)](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)

   ```bash
   aws configure
   ```

3. **Bedrock Model Access**: Enable access to Amazon Bedrock Anthropic Claude models in your AWS region
   - Navigate to [Amazon Bedrock](https://console.aws.amazon.com/bedrock/)
   - Go to "Model access" and request access to:
     - Anthropic Claude 3.5 Sonnet model
     - Anthropic Claude 3.5 Haiku model
   - [Bedrock Model Access Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)

4. **Python 3.10+**: Required for running the application
   - [Python Downloads](https://www.python.org/downloads/)

## Deploy

1. **Create infrastructure**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r dev-requirements.txt

    chmod +x scripts/prereq.sh
    ./scripts/prereq.sh

    chmod +x scripts/list_ssm_parameters.sh
    ./scripts/list_ssm_parameters.sh
    ```

    > [!CAUTION]
    > Please prefix all the resource names with your chosen prefix (e.g., `myapp`).

2. **Create Agentcore Gateway**

    ```bash
    python scripts/agentcore_gateway.py create --name myapp-gw
    ```

3. **Setup Agentcore Identity**

    ```bash
    python scripts/cognito_credentials_provider.py create --name myapp-cp

    python test/test_gateway.py --prompt "Hello, can you help me?"
    ```

4. **Create Memory**

    ```bash
    python scripts/agentcore_memory.py create --name myapp

    python test/test_memory.py load-conversation
    python test/test_memory.py load-prompt "My preferred response format is detailed explanations"
    python test/test_memory.py list-memory
    ```

5. **Setup Agent Runtime**

> [!CAUTION]
> Please ensure the name of the agent starts with your chosen prefix.
    
  ```bash
  agentcore configure --entrypoint main.py -er arn:aws:iam::<Account-Id>:role/<Role> --name myapp<AgentName>
  ```

  Use `./scripts/list_ssm_parameters.sh` to fill:
  - `Role = ValueOf(/app/myapp/agentcore/runtime_iam_role)`
  - `OAuth Discovery URL = ValueOf(/app/myapp/agentcore/cognito_discovery_url)`
  - `OAuth client id = ValueOf(/app/myapp/agentcore/web_client_id)`.

  > [!CAUTION]
  > Please make sure to delete `.agentcore.yaml` before running agentcore launch.

  ```bash
  rm .agentcore.yaml

  agentcore launch

  python test/test_agent.py myapp<AgentName> -p "Hi"
  ```

6. **Local Host Streamlit UI**

> [!CAUTION]
> Streamlit app should only run on port `8501`.

```bash
streamlit run app.py --server.port 8501 -- --agent=myapp<AgentName>
```

## Sample Queries

1. Hello, can you help me with information?

2. What tools do you have available?

3. Can you remember my preferences?

4. What can you tell me about your capabilities?

## Scripts

### Amazon Bedrock AgentCore Gateway

```bash
# Create gateway
python scripts/agentcore_gateway.py create --name myapp-gw

# Delete gateway
python scripts/agentcore_gateway.py delete
```

### Amazon Bedrock AgentCore Memory

```bash
# Create memory
python scripts/agentcore_memory.py create --name MyMemory

# Delete memory
python scripts/agentcore_memory.py delete
```

### Cognito Credentials Provider

```bash
# Create provider
python scripts/cognito_credentials_provider.py create --name myapp-cp

# Delete provider
python scripts/cognito_credentials_provider.py delete
```

### Agent Runtime

```bash
# Delete agent runtime
python scripts/agentcore_agent_runtime.py myapp<AgentName>
```

## Cleanup

```bash
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh

python scripts/cognito_credentials_provider.py delete
python scripts/agentcore_memory.py delete
python scripts/agentcore_gateway.py delete
python scripts/agentcore_agent_runtime.py myapp<AgentName>

rm .agentcore.yaml
rm .bedrock_agentcore.yaml
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](../../CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.
