# Technology Stack

## Core Frameworks (v2 - CURRENT)

**Use these for all new development:**

- **Amazon Bedrock AgentCore**: Primary agent infrastructure platform (Runtime, Gateway, Identity, Memory, Observability)
- **Strands Agents**: Framework for building AI agents (`strands-agents`, `strands-agents-tools`)
- **AWS SDK**: `boto3`, `botocore` for AWS service integration

## Legacy Frameworks (v1 - DEPRECATED)

**⚠️ Do NOT use for new development:**

- **Amazon Bedrock Agents (v1)**: Older agent framework using `AWS::Bedrock::Agent` CloudFormation resources
- Some catalog agents still use this approach but are being migrated
- Legacy agents lack AgentCore's observability, memory, and gateway features

## Languages & Runtimes

- **Python 3.10+**: Primary language for agents and backend
- **Node.js/TypeScript**: For React UI components
- **Shell Scripts**: Deployment and automation (bash/zsh)

## Key Python Libraries

- `bedrock-agentcore` - AgentCore SDK
- `bedrock-agentcore-starter-toolkit` - Starter utilities
- `strands-agents` - Agent framework
- `streamlit` - Local UI development
- `fastmcp` - Model Context Protocol
- `pydantic` - Data validation
- `PyYAML` - Configuration management
- `requests`, `httpx` - HTTP clients
- `pandas` - Data processing
- `opensearch-py` - Search functionality

## Frontend Stack

- **Next.js 15+** with React 19
- **TypeScript 5**
- **Tailwind CSS 4**
- **AWS SDK for JavaScript** (`@aws-sdk/client-bedrock*`)
- **Framer Motion** for animations

## Infrastructure & Deployment

### Current Approach (v2)
- **AWS CloudFormation**: Infrastructure as Code for AgentCore components
- **Docker**: Container packaging for AgentCore runtimes
- **Amazon ECR**: Container registry for agent runtime images
- **AWS Lambda**: Serverless compute for AgentCore Gateway targets
- **AWS CodeBuild**: CI/CD for packaging

### Legacy Approach (v1 - DEPRECATED)
- **AWS CDK**: Used in some older agents
- **Lambda Action Groups**: Direct Lambda integration (replaced by AgentCore Gateway)
- **AWS::Bedrock::Agent**: CloudFormation resource type (deprecated)

## Development Tools

- **uv**: Fast Python package installer (preferred over pip)
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking
- **pre-commit**: Git hooks

## Identifying Agent Version

### AgentCore + Strands (v2 - CURRENT)
Look for these indicators:
- Uses `agentcore_template/` structure
- Has `strands-agents` in requirements
- Uses `agentcore configure` and `agentcore launch` commands
- CloudFormation uses IAM roles for `bedrock-agentcore.amazonaws.com`
- Has gateway, memory, and identity components

### Bedrock Agents (v1 - DEPRECATED)
Look for these indicators:
- CloudFormation uses `AWS::Bedrock::Agent` resource type
- Has `ActionGroups` with direct Lambda integration
- Uses `bedrock:InvokeAgent` API calls
- No gateway, memory, or identity separation
- **Do not use as template for new agents**

## Common Commands

### Python Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
uv pip install -r requirements.txt
uv pip install -r dev-requirements.txt
```

### AgentCore Template Deployment
```bash
# Deploy infrastructure
chmod +x scripts/prereq.sh
./scripts/prereq.sh

# Create gateway
python scripts/agentcore_gateway.py create --name myapp-gw

# Create identity provider
python scripts/cognito_credentials_provider.py create --name myapp-cp

# Create memory
python scripts/agentcore_memory.py create --name myapp

# Configure agent runtime
agentcore configure --entrypoint main.py -rf agent/requirements.txt -er <IAM_ROLE_ARN> --name myapp<AgentName>

# Launch agent
rm .agentcore.yaml  # Important: delete before launch
agentcore launch

# Run Streamlit UI (IAM auth)
streamlit run app.py --server.port 8501

# Run Streamlit UI (OAuth auth)
streamlit run app_oauth.py --server.port 8501 -- --agent=myapp<AgentName>
```

### Testing
```bash
# Test gateway
python tests/test_gateway.py --prompt "Hello, can you help me?"

# Test memory
python tests/test_memory.py load-conversation
python tests/test_memory.py list-memory

# Test agent
python tests/test_agent.py myapp<AgentName> -p "Hi"
```

### Cleanup
```bash
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh

python scripts/cognito_credentials_provider.py delete
python scripts/agentcore_memory.py delete
python scripts/agentcore_gateway.py delete
python scripts/agentcore_agent_runtime.py myapp<AgentName>
```

### UI Development
```bash
cd ui
npm install
npm run dev      # Development server
npm run build    # Production build
npm start        # Production server
npm run lint     # Linting
```

### CloudFormation Deployment

#### AgentCore Template (v2 - RECOMMENDED)
```bash
# Deploy AgentCore infrastructure
cd agentcore_template
chmod +x scripts/prereq.sh
./scripts/prereq.sh

# Follow AgentCore deployment steps (see above)
```

#### Legacy Agents (v1 - DEPRECATED)
```bash
# Some catalog agents still use legacy Bedrock Agents
# These are maintained for reference only
aws cloudformation create-stack \
  --stack-name my-legacy-agent \
  --template-body file://agents_catalog/XX-agent-name/agent-cfn.yaml \
  --parameters ParameterKey=AgentIAMRoleArn,ParameterValue=<ROLE_ARN> \
  --capabilities CAPABILITY_IAM

# NOTE: Do not use legacy agents as templates for new development
```

## AWS Services Used

- Amazon Bedrock (Claude models, AgentCore)
- AWS Lambda
- Amazon S3
- Amazon ECR
- AWS IAM
- Amazon Cognito
- AWS Systems Manager (Parameter Store)
- Amazon CloudWatch (Logs, Metrics, Observability)
- AWS X-Ray (Tracing)
- Amazon OpenSearch
- Amazon VPC
- AWS Secrets Manager

## Model Context Protocol (MCP)

Recommended MCP servers for AI-assisted development:
- `awslabs.aws-documentation-mcp-server` - AWS docs
- `awslabs.cfn-mcp-server` - CloudFormation assistance
- `awslabs.git-repo-research-mcp-server` - Repository research

Install via `uvx` (requires `uv` package manager).

## Development Guidelines

### For New Agent Development
1. **Always start from `agentcore_template/`** - This is the only approved starting point
2. Use Strands framework for tool development
3. Deploy with AgentCore components (Gateway, Memory, Identity)
4. Follow the v2 deployment commands above

### When Working with Existing Agents
1. **Check the agent version first** using the indicators above
2. If it's v1 (Bedrock Agents), consider it reference-only
3. Do not copy v1 patterns into new code
4. When modernizing v1 agents, rebuild from `agentcore_template/` rather than modifying in place

### Repository Context
- This repository serves as a **catalog of HCLS use cases**, not all implementations are current
- v1 agents demonstrate use cases but use deprecated technology
- Focus community contributions on v2 (AgentCore + Strands) implementations
- When in doubt, reference `agentcore_template/` or `agents_catalog/28-Research-agent-biomni-gateway-tools/`
