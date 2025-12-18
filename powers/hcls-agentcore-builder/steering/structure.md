# Project Structure

## Root Directory

```
├── agentcore_template/          # End-to-end AgentCore deployment template
├── agents_catalog/              # Library of 30+ specialized HCLS agents
├── multi_agent_collaboration/   # Multi-agent collaboration examples
├── evaluations/                 # Agent performance evaluation tools
├── ui/                          # React-based web interface
├── docs/                        # Documentation site (Astro)
├── build/                       # CloudFormation build templates
├── Infra_cfn.yaml              # Main infrastructure stack
└── CONTRIBUTING.md             # Contribution guidelines
```

## AgentCore Template Structure

The `agentcore_template/` directory provides a complete reference implementation:

```
agentcore_template/
├── agent/
│   ├── agent_config/           # Agent configuration modules
│   │   ├── tools/              # Local agent tools
│   │   ├── agent.py            # Agent definition
│   │   ├── agent_task.py       # Task handling
│   │   ├── context.py          # Context management
│   │   ├── memory_hook_provider.py
│   │   └── streaming_queue.py
│   └── requirements.txt        # Agent dependencies
├── app_modules/                # Streamlit UI modules
├── prerequisite/               # Infrastructure prerequisites
│   ├── lambda/                 # Lambda function code for gateway
│   ├── infrastructure.yaml     # CloudFormation template
│   ├── cognito.yaml           # Cognito configuration
│   └── prereqs_config.yaml    # Configuration file
├── scripts/                    # Deployment and management scripts
│   ├── prereq.sh              # Deploy prerequisites
│   ├── agentcore_gateway.py   # Gateway management
│   ├── agentcore_memory.py    # Memory management
│   ├── agentcore_agent_runtime.py
│   ├── cognito_credentials_provider.py
│   ├── cleanup.sh             # Cleanup script
│   └── utils.py
├── tests/                      # Test scripts
├── static/                     # Static assets (fonts, images)
├── app.py                      # Streamlit app (IAM auth)
├── app_oauth.py               # Streamlit app (OAuth auth)
└── main.py                    # Agent entrypoint
```

## Agents Catalog Structure

**⚠️ Important:** The agents catalog contains a mix of v1 (deprecated Bedrock Agents) and v2 (AgentCore + Strands) implementations. Always use `agentcore_template/` as your starting point for new agents.

### v2 Pattern (Recommended - AgentCore + Strands)

Use this structure for new agents:
```
agents_catalog/XX-agent-name/
├── README.md                   # Agent documentation
├── agent/
│   ├── agent_config/           # Agent configuration
│   │   ├── tools/              # Local Strands tools
│   │   └── agent.py            # Agent definition
│   └── requirements.txt        # Agent dependencies
├── prerequisite/               # Infrastructure
│   ├── lambda/                 # Gateway Lambda functions
│   └── infrastructure.yaml     # CloudFormation
├── scripts/                    # Deployment scripts
├── app.py                      # Streamlit UI (optional)
└── main.py                    # Agent entrypoint
```

### v1 Pattern (Legacy - Bedrock Agents - DO NOT USE)

Many existing agents still use this deprecated pattern:
```
agents_catalog/XX-agent-name/
├── README.md                   # Agent documentation
├── action-groups/              # ⚠️ Legacy action groups
│   └── action-name/
│       ├── lambda_function.py  # Lambda handler
│       ├── api_schema.yaml    # OpenAPI schema
│       └── container/         # Docker container
├── agent-cfn.yaml             # ⚠️ Uses AWS::Bedrock::Agent
└── deploy.sh
```

**How to identify v1 agents:**
- Uses `action-groups/` directory structure
- CloudFormation templates contain `AWS::Bedrock::Agent` resources
- No `agent/agent_config/` directory
- No Strands framework dependencies

**Do not use v1 agents as templates.** They are kept for reference and backward compatibility only.

### Agent Numbering Convention

- `00-09`: Setup and environment
- `10-19`: Research and information retrieval agents
- `20-29`: Analysis and processing agents
- `30-39`: Integration and workflow agents

### v2 Examples in Catalog

Reference these for modern implementations:
- `17-variant-interpreter-agent/advanced-strands-agentcore/` - Strands + AgentCore
- `28-Research-agent-biomni-gateway-tools/` - Full AgentCore template with gateway tools

## Multi-Agent Collaboration Structure

```
multi_agent_collaboration/
├── cancer_biomarker_discovery/
│   ├── bedrock_agents/        # ⚠️ v1 Legacy - Bedrock Agents (deprecated)
│   └── strands_agentcore/     # ✅ v2 Recommended - Strands + AgentCore
├── Clinical-Trial-Protocol-Assistant/  # ⚠️ v1 Legacy
├── competitive_intelligence/           # ⚠️ v1 Legacy
└── hypothesis_generation_inline/       # ⚠️ v1 Legacy
```

**For multi-agent systems, use:** `cancer_biomarker_discovery/strands_agentcore/` as the reference implementation.

## UI Structure

```
ui/
├── app/                       # Next.js app directory
│   ├── api/                   # API routes
│   ├── chat/                  # Chat interface
│   └── globals.css
├── cloudformation/            # ECS deployment templates
├── public/                    # Static assets
└── package.json
```

## Key Configuration Files

### Agent Configuration
- `agent/agent_config/agent.py` - Agent definition and tool registration
- `agent/agent_config/tools/` - Local tool implementations
- `prerequisite/prereqs_config.yaml` - Infrastructure configuration

### CloudFormation Templates
- `Infra_cfn.yaml` - Main stack deploying all agents (⚠️ contains v1 legacy agents)
- `agents_catalog/*/agent-cfn.yaml` - Individual agent stacks (⚠️ many are v1 legacy)
- `agentcore_template/prerequisite/infrastructure.yaml` - v2 base infrastructure (✅ use this)
- `build/*.yaml` - Reusable CloudFormation components

### Python Requirements
- `agent/requirements.txt` - Agent runtime dependencies
- `dev-requirements.txt` - Development dependencies
- `requirements.txt` - General dependencies

### SSM Parameters
Configuration stored in AWS Systems Manager Parameter Store:
- `/app/myapp/agentcore/runtime_iam_role` - Runtime IAM role ARN
- `/app/myapp/agentcore/gateway_iam_role` - Gateway IAM role ARN
- `/app/myapp/agentcore/lambda_arn` - Lambda function ARN
- `/app/myapp/agentcore/cognito_discovery_url` - OAuth discovery URL
- `/app/myapp/agentcore/web_client_id` - OAuth client ID

## Naming Conventions

### Resource Naming
- Prefix all resources with a consistent identifier (e.g., `myapp`)
- Agent names: `myapp<AgentName>` (e.g., `myappResearchAgent`)
- Gateway names: `myapp-gw`
- Memory names: `myapp` or `myapp-memory`
- Credentials provider: `myapp-cp`

### File Naming
- Python modules: `snake_case.py`
- CloudFormation templates: `kebab-case.yaml` or `PascalCase.yaml`
- Shell scripts: `snake_case.sh`
- Configuration files: `snake_case.yaml`

### Code Organization
- Lambda handlers: `lambda_function.py` with `lambda_handler` function
- Agent tools: Organized in `agent_config/tools/` directory
- Tests: Mirror source structure in `tests/` directory
- Scripts: Utility scripts in `scripts/` directory

## Creating a New Agent (v2 Approach)

**Always start from `agentcore_template/` - never use catalog agents as templates.**

When creating a new agent:
1. Copy the entire `agentcore_template/` directory
2. Modify `agent/agent_config/tools/` - Add your custom Strands tools
3. Update `agent/agent_config/agent.py` - Configure agent behavior and tool registration
4. Add gateway tools in `prerequisite/lambda/` - Lambda functions for external APIs
5. Update `prerequisite/prereqs_config.yaml` - Configuration values
6. Modify `prerequisite/infrastructure.yaml` - Add required AWS resources (IAM, Lambda, etc.)
7. Update resource naming to use your chosen prefix (replace `myapp`)

**Do not:**
- Copy agents from `agents_catalog/` that use `action-groups/` structure
- Use CloudFormation templates with `AWS::Bedrock::Agent` resources
- Reference v1 multi-agent examples as starting points

## Build Artifacts

Generated during deployment (not in version control):
- `.agentcore.yaml` - AgentCore configuration (delete before relaunch)
- `.bedrock_agentcore.yaml` - Bedrock AgentCore state
- `.venv/` - Python virtual environment
- `node_modules/` - Node.js dependencies
- `build/` - Compiled CloudFormation templates
