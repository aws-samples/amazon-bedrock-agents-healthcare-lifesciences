# Research agent with Biomni gateway on Amazon Bedrock AgentCore

> [!IMPORTANT]
> This is a biomedical research agent with multiple tools using Amazon Bedrock AgentCore framework with Strands. The agent can connect to your own data infrastructure with your own local tools like PubMed and knowledge base, includes a sample public tools gateway, Amazon Cognito identity, memory, observability and a local Streamlit UI.
NOTE: The public tools gateway includes all the database tools from Biomni https://github.com/snap-stanford/Biomni/tree/main/biomni/tool

The template provides you two options for authentication with the AgentCore Runtime - you can either deploy the runtime with OAuth authentication or IAM authentication. Based on your choice, you can run a local streamlit app with /without Cogntio authentication. The runtime internally will use M2M auth flow to connect with the AgentCore Gateway.

![architecture](image.png)

## Table of Contents

- [Research agent with Biomni gateway on Amazon Bedrock AgentCore](#research-agent-with-biomni-gateway-on-amazon-bedrock-agentcore)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
    - [AWS Account Setup](#aws-account-setup)
  - [Deploy](#deploy)
  - [Sample Queries](#sample-queries)
  - [Scripts](#scripts)
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

3. **Bedrock Models:
For this application, we will be leveraging LLM models provided through Amazon Bedrock. 
   - claude-sonnet-4
   - Other models such as: gpt-oss-120b, amazon-nova-premier, etc.\

4. Download Database files
   
    ```bash
    cd prerequisite/lambda-database/python && mkdir schema_db && cd schema_db
    curl -s https://api.github.com/repos/snap-stanford/Biomni/contents/biomni/tool/schema_db | grep '"download_url"' | cut -d '"' -f 4 | xargs -n 1 wget
    cd ../../../../
    ```

## Deploy

1. **Setup agent tools**
    - Review the sample agent local tools under 'agent_config/tools/research_tools.py' and add/modify your own tools if required. We provide PubMed as a local tool. 
    - Clone the Biomni code repository and copy the schema files for the database tools from https://github.com/snap-stanford/Biomni/tree/main/biomni/tool/schema_db to 'prerequisite/lambda/python/schema_db'. Note, we provide the Biomni database tools adapted with Bedrock Converse API in 'prerequisite/lambda-database/python/database.py' and have removed the following commercial license tools 'kegg', 'iucn', and 'remap'.   You can review the gateway lambda tools under 'prerequisite/lambda-database' and add/modify your own lambda tools if required. 

2. **Create infrastructure**

Set up the Python environment and deploy AWS resources:

    ```bash
    uv sync
    # source .venv/bin/activate if environment already exists
    uv add -r dev-requirements.txt

    chmod +x scripts/prereq.sh
    ./scripts/prereq.sh
    ```
This creates:
   - 2 Lambda functions (database and literature tools)
   - AgentCore Gateway to register the tools
   - AgentCore Memory for session/memory management
   - Supporting AWS resources via CloudFormation

Verify the deployment:

    ```bash
    chmod +x scripts/list_ssm_parameters.sh
    ./scripts/list_ssm_parameters.sh
    ```

    > [!CAUTION]
    > Please prefix all the resource names with your chosen prefix (e.g., `researchapp`).

1. **Setup Agentcore Identity**
    You can look to reuse the credentials provider user pool across multiple deployments if required.
    
    ```bash
    uv run scripts/cognito_credentials_provider.py create --name researchapp-cp
    uv run tests/test_gateway.py --prompt "What tools are available?"
    uv run tests/test_gateway.py --prompt "Find information about human insulin protein" --use-search
    ```
     For the current implementation, we do not use the decorator function to get the access token for the gateway. Rather we fetch it by directly retrieving the cognito domain, resource server, user pool. 

2. **Test Memory**
    The memory has been created as part of the deployment process in step 1. Let's test it. 

    ```bash
    uv run tests/test_memory.py load-conversation
    uv run tests/test_memory.py load-prompt "My preferred response format is detailed explanations"
    uv run tests/test_memory.py list-memory
    ```

3. **Test local deployment of Agent**

    ```bash
    uv run tests/test_agent_locally.py --prompt "Find information about human insulin protein"
    ```

4. **Setup Agent Runtime**

> [!CAUTION]
> Please ensure the name of the agent starts with your chosen prefix.
Note : We have decoupled the OAuth authentication of the Gateway from the Runtime. This means that you can use the Runtime either with IAM or OAuth authentication. The gateway bearer token will be retrieved using M2M authentication internally. 

  ```bash
  uv run agentcore configure --entrypoint main.py -er arn:aws:iam::<Account-Id>:role/<Role> --name researchapp<AgentName>
  uv run agentcore configure --entrypoint main.py -er arn:aws:iam::<Account-Id>:role/<Role> --name researchapp<AgentName> --use-search
  ```
If you want to use OAuth authentication, enter 'yes' for OAuth. 

  Use `./scripts/list_ssm_parameters.sh` to fill:
  - `Role = ValueOf(/app/researchapp/agentcore/runtime_iam_role)`
  - `OAuth Discovery URL = ValueOf(/app/researchapp/agentcore/cognito_discovery_url)`
  - `OAuth client id = ValueOf(/app/researchapp/agentcore/web_client_id)`.

  > [!CAUTION]
  > Please make sure to delete `.agentcore.yaml` before running agentcore launch.

  ```bash
  rm .agentcore.yaml

  agentcore launch
  ```
  If you are using IAM based authenticaiton, invoke directly
  ```
  uv run agentcore invoke '{"prompt": "Find information about human insulin protein"}'
  ```
  If you are using OAuth authentication, invoke via HTTPS endpoint like the script below 
  ```
  uv run tests/test_agent.py researchapp<AgentName> -p "Hi"
  ```

6. **Local Host Streamlit UI**

> [!CAUTION]
> Streamlit app should only run on port `8501`.
If you are using IAM based authenticaiton, run streamlit and select the agent runtime you would like to use
```bash
uv run streamlit run app.py --server.port 8501 
```
If you are using OAuth authentication, specify the particular agent app, and authenticate yourself 
```bash
uv run streamlit run app_oauth.py --server.port 8501 -- --agent=researchapp<AgentName>
```
![streamlit_screen](streamlit_screenshot.png)

## Sample Queries

1. Conduct a comprehensive analysis of trastuzumab (Herceptin) mechanism of action, and resistance mechanisms. 
    I need:
    1. HER2 protein structure and binding sites
    2. Downstream signaling pathways affected
    3. Known resistance mechanisms from clinical data and adverse events from OpenFDA data
    4. Current clinical trials investigating combination therapies
    5. Biomarkers for treatment response prediction
    
    Please query relevant databases to provide a comprehensive research report.

2. Analyze the clinical significance of BRCA1 variants in breast cancer risk and treatment response.
    Please investigate:
    1. Population frequencies of pathogenic BRCA1 variants
    2. Clinical significance and pathogenicity classifications
    3. Associated cancer risks and penetrance estimates
    4. Treatment implications (PARP inhibitors, platinum agents)
    5. Current clinical trials for BRCA1-positive patients
    
    Use multiple databases to provide comprehensive evidence.

3. Investigate the PI3K/AKT/mTOR pathway in cancer and identify potential therapeutic targets.
    Research focus:
    1. Key proteins and their interactions in the pathway
    2. Pathway alterations in different cancer types
    3. Current therapeutic agents targeting this pathway
    4. Resistance mechanisms and combination strategies
    5. Biomarkers for pathway activation and drug response
    
    Synthesize data from pathway, protein, and clinical databases.

4. What can you tell me about your capabilities?

7. **Setup AgentCore Observability dashboard**
You are able to view all your Agents that have observability in them and filter the data based on time frames as described [here](https://aws.amazon.com/blogs/machine-learning/build-trustworthy-ai-agents-with-amazon-bedrock-agentcore-observability/)
You will need to Enable Transaction Search on Amazon CloudWatch as described [here](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html)

## Scripts

### Cognito Credentials Provider

```bash
# Create provider
uv run scripts/cognito_credentials_provider.py create --name researchapp-cp

# Delete provider
uv run scripts/cognito_credentials_provider.py delete
```

### Agent Runtime

```bash
# Delete agent runtime
uv run scripts/agentcore_agent_runtime.py researchapp<AgentName>
```

## Cleanup

```bash
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh

uv run scripts/cognito_credentials_provider.py delete
uv run scripts/agentcore_memory.py delete
uv run scripts/agentcore_gateway.py delete
uv run scripts/agentcore_agent_runtime.py researchapp<AgentName>

rm .agentcore.yaml
rm .bedrock_agentcore.yaml
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](../../CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.
