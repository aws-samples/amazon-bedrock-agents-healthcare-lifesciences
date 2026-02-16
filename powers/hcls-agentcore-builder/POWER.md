---
name: "hcls-agentcore-builder"
displayName: "HCLS AgentCore Builder"
description: "Complete guide for building production-ready Healthcare and Life Sciences AI agents using Amazon Bedrock AgentCore and Strands framework with best practices, patterns, and step-by-step workflows."
keywords: ["agentcore", "bedrock", "hcls", "healthcare", "strands", "agents", "production", "aws"]
author: "AWS HCLS Agent Community"
---

# HCLS AgentCore Builder

## Overview

Welcome to the Healthcare and Life Sciences (HCLS) AgentCore Builder power! This guide helps you build production-ready AI agents using Amazon Bedrock AgentCore and the Strands framework.

**Target Audience:** Developers building their first AgentCore agent for healthcare and life sciences workflows.

### 🚀 Quick Start: Your Two Essential References

**The repository provides two critical references:**

#### 1. **agentcore_template/** - Your Starting Point
- **Purpose:** Complete foundation for building any new agent
- **Use when:** Starting a new agent from scratch
- **What it provides:** End-to-end AgentCore setup with sample tools, deployment scripts, and Streamlit UI
- **Action:** Navigate to `agentcore_template/` and follow the README step-by-step

#### 2. **agents_catalog/28-Research-agent-biomni-gateway-tools/** - Production Reference
- **Purpose:** Production-ready implementation with 30+ database tools
- **Use when:** Need advanced patterns and real-world examples
- **What it provides:** Database tools, advanced gateway patterns, production-scale organization
- **Action:** Study this agent's structure and README for production patterns

**Start with the template, reference the research agent for advanced patterns.**

### What This Power Provides

- Step-by-step workflows from POC to production
- Best practices for production-ready agentic AI systems
- Agent patterns for common HCLS use cases
- Integration with MCP servers for documentation
- Detailed explanations of concepts in the template

## Available Resources

### MCP Servers

This power works with two MCP servers for comprehensive documentation:

1. **AgentCore MCP Server** - Search AgentCore documentation and API references
2. **Strands Agents MCP Server** - Search Strands framework documentation

### Steering Files

This power includes three steering files with detailed repository knowledge. Access them using the `readSteering` action:

- **product.md** - Repository overview, key components, and deployment approaches (v2 vs v1)
- **structure.md** - Complete project structure, file organization, naming conventions, and how to create new agents
- **tech.md** - Technology stack, frameworks, AWS services, common commands, and development guidelines

**To read a steering file:**
```
Call action "readSteering" with powerName="hcls-agentcore-builder", steeringFile="product.md"
```

These files provide comprehensive context about the repository structure, technology choices, and best practices.

## Getting Started

### Prerequisites

**AWS Setup:**
- AWS account with appropriate permissions
- AWS CLI configured with credentials
- Access to Amazon Bedrock (Claude 3.7 Sonnet or later)
- IAM roles for AgentCore services

**Development Environment:**
- Python 3.10+ installed
- `uv` package manager (preferred) or `pip`
- Git for version control

**Knowledge Requirements:**
- Basic Python programming
- Understanding of AWS services (Lambda, S3, IAM)
- Familiarity with REST APIs
- Basic understanding of AI/LLM concepts

### Installation Verification

```bash
# Verify Python version
python --version  # Should be 3.10+

# Verify AWS CLI
aws --version
aws sts get-caller-identity

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

## Core Design Principles

### Foundational Characteristics

**Asynchronous Operation**
- Design agents for loosely coupled, event-rich environments
- Use event-driven communication over direct calls

**Autonomous Behavior**
- Create agents that act independently without constant supervision
- Enable decision-making based on programming and context

**Goal-Oriented Agency**
- Ensure agents act with purpose toward specific goals
- Align agent behavior with user intent

### Architectural Principles

**Composability** - Build modular patterns that can be combined

**Contextuality** - Select patterns based on specific use cases and constraints

**Cloud-Native** - Leverage AWS managed services to minimize operational overhead

## Agent Patterns for HCLS

### 1. Basic Reasoning Agents

**When to Use:** Conversational Q&A, policy explanations, decision guidance

**Implementation:** Use as foundation for complex patterns, implement prompt engineering, keep stateless

**AWS Services:** Amazon Bedrock, API Gateway, Lambda

### 2. Retrieval-Augmented Generation (RAG) Agents

**When to Use:** Responses must be grounded in up-to-date, factual information

**Implementation:** Add domain-specific knowledge, implement context windowing, ensure quality semantic search

**AWS Services:** Bedrock, Kendra, OpenSearch, S3, Lambda

### 3. Tool-Based Agents

**When to Use:** Agents need to perform actions beyond text generation (API calls, database queries, system operations)

**Implementation:** Define clear tool schemas, design atomic single-purpose tools, implement proper error handling

**AWS Services:** Bedrock with function-calling, Lambda, API Gateway, EventBridge

### 4. Workflow Orchestration Agents

**When to Use:** Coordinating multi-step tasks by breaking down complex objectives

**Implementation:** Separate orchestration from execution, implement state tracking, create composable workflows

**AWS Services:** Bedrock, Step Functions, EventBridge, Lambda, DynamoDB

### 5. Multi-Agent Collaboration

**When to Use:** Complex problem-solving requiring division of labor and specialized expertise

**Implementation:** Design clear communication protocols, define role-based responsibilities, implement coordination mechanisms

**AWS Services:** Bedrock, SQS, EventBridge, DynamoDB, Step Functions

## Building Your First Agent: 6-Stage Workflow

### Quick Start

**Follow the agentcore_template README for complete step-by-step instructions.**

The sections below expand on the template with additional context and best practices.

### Stage 1: Create Agent Proof of Concept

#### Set Up Environment

```bash
# Clone repository
git clone https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences.git
cd amazon-bedrock-agents-healthcare-lifesciences/agentcore_template

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -r dev-requirements.txt
```

#### Define Agent Tools

**Best Practice:** Start with 2-3 core tools, test thoroughly, then expand.

**Review template's sample tools:**
- Local tools: `agent/agent_config/tools/sample_tools.py`
- Gateway Lambda tools: `prerequisite/lambda/`

**Tool Design Checklist:**
- [ ] Clear, descriptive function name
- [ ] Comprehensive docstring
- [ ] Type hints for all parameters
- [ ] Single, well-defined purpose
- [ ] Proper error handling
- [ ] Returns structured data

#### Test POC

**POC Validation Checklist:**
- [ ] Agent handles core use cases
- [ ] Tool selection is appropriate
- [ ] Response quality meets standards
- [ ] No critical errors
- [ ] Stakeholder approval received

### Stage 2: Add Persistent Memory

```bash
# Create memory resource
python scripts/agentcore_memory.py create --name myapp
```

**Memory Strategies:**
- **USER_PREFERENCE** - Automatically extract customer preferences and behavior patterns
- **SEMANTIC** - Capture factual information with vector embeddings for semantic search

**Memory Testing Checklist:**
- [ ] Preferences correctly stored and recalled
- [ ] Semantic information accurately retrieved
- [ ] No cross-user memory contamination
- [ ] Retrieval latency acceptable (<200ms)

### Stage 3: Centralize Tools via Gateway

**The template includes sample gateway Lambda tools.**

**For production example with 30+ tools, see:** `agents_catalog/28-Research-agent-biomni-gateway-tools/prerequisite/lambda-database/`

```bash
# Create gateway
python scripts/agentcore_gateway.py create --name myapp-gw
```

**Gateway Benefits:**
- Centralized tool management
- Reusable across multiple agents
- Easier updates and maintenance
- Better security and access control

### Stage 4: Add Authentication & Security

```bash
# Create Cognito-based identity provider
python scripts/cognito_credentials_provider.py create --name myapp-cp
```

**Security Checklist:**
- [ ] JWT token validation configured
- [ ] IAM permissions follow least-privilege
- [ ] Sensitive data handling verified
- [ ] Audit logging enabled
- [ ] HIPAA compliance reviewed (if handling PHI)
- [ ] AWS BAA in place (if handling PHI)

### Stage 5: Deploy to Production

```bash
# Deploy infrastructure
chmod +x scripts/prereq.sh
./scripts/prereq.sh

# Configure agent runtime
agentcore configure --entrypoint main.py -rf agent/requirements.txt -er <IAM_ROLE_ARN> --name myappAgentName

# Launch agent
rm .agentcore.yaml
agentcore launch
```

**Deployment Options:**
- **Streamlit (Development):** `streamlit run app.py --server.port 8501`
- **Streamlit with OAuth:** `streamlit run app_oauth.py --server.port 8501 -- --agent=myappAgentName`
- **React (Production):** Deploy via `ui/` directory

**Production Checklist:**
- [ ] Container-based deployment configured
- [ ] Auto-scaling policies defined
- [ ] Session management implemented
- [ ] Monitoring and observability enabled
- [ ] Cost tracking configured

### Stage 6: Implement Observability

**Key Metrics to Track:**
- Request latency and throughput
- Tool invocation success rates
- Memory retrieval performance
- Token usage and costs
- Error rates by component

**Set up CloudWatch dashboards and alerts for production monitoring.**

## LLM Workflow Patterns

### Prompt Chaining
Break complex reasoning into modular, auditable steps. Use for multi-step analysis and tasks exceeding context windows.

### Routing
Intelligent task classification and delegation to specialized agents. Use for multi-domain queries.

### Parallelization
Concurrent execution of independent subtasks to reduce latency. Use for multiple database queries or batch processing.

### Orchestration
Centralized task decomposition with coordinator-worker hierarchy. Use for complex multi-agent workflows.

### Evaluator/Reflect-Refine Loops
Self-improvement through feedback and iteration. Use for quality assurance and iterative refinement.

## Best Practices Summary

### Tool Design
✅ **DO:**
- Create atomic, single-purpose tools
- Write comprehensive docstrings
- Implement proper error handling
- Use clear, descriptive names
- Return structured data

❌ **DON'T:**
- Create overly complex multi-purpose tools
- Skip error handling
- Use vague tool names
- Return unstructured text

### Memory Management
✅ **DO:**
- Use USER_PREFERENCE for preferences and behavior
- Use SEMANTIC for factual information
- Implement relevance-based retrieval
- Test cross-session continuity

❌ **DON'T:**
- Inject all historical context
- Mix memory types inappropriately
- Skip memory isolation testing

### Security
✅ **DO:**
- Implement JWT-based authentication
- Follow least-privilege IAM permissions
- Enable audit logging
- Review HIPAA compliance for PHI

❌ **DON'T:**
- Hardcode credentials
- Use overly permissive IAM roles
- Handle PHI without AWS BAA

### Production Deployment
✅ **DO:**
- Use container-based deployment
- Implement auto-scaling
- Configure comprehensive monitoring
- Set up cost tracking

❌ **DON'T:**
- Deploy without monitoring
- Skip load testing
- Ignore cost optimization

## Common Pitfalls to Avoid

| Pitfall | Solution |
|---------|----------|
| Memory overload | Use relevance-based retrieval with top_k |
| Tool proliferation | Consolidate and reuse via Gateway |
| Synchronous blocking | Design for async, event-driven operations |
| Insufficient error handling | Implement comprehensive error recovery |
| Security afterthought | Build security in from the beginning |
| Missing observability | Implement monitoring before production |
| Inadequate testing | Test with realistic scenarios and edge cases |

## Success Criteria

### Technical Metrics
- Response latency <2 seconds (p95)
- Tool invocation success rate >99%
- Memory retrieval accuracy >90%
- System uptime >99.9%

### Business Metrics
- User satisfaction score >4.5/5
- Task completion rate >85%
- Cost per interaction within budget
- Time to resolution improved

## Example Agents in Repository

### Primary References

#### 1. AgentCore Template
**Location:** `agentcore_template/`

**Key Features:**
- End-to-end AgentCore setup (Runtime, Gateway, Identity, Memory, Observability)
- Sample local tools and gateway Lambda tools
- Streamlit UI with OAuth/IAM authentication
- Comprehensive deployment scripts

**When to use:** Building a new agent from scratch

**README:** Follow `agentcore_template/README.md` step-by-step

#### 2. Research Agent with Database Tools
**Location:** `agents_catalog/28-Research-agent-biomni-gateway-tools/`

**Key Features:**
- 30+ database tools via Gateway
- Advanced tool organization patterns
- Production-ready implementation
- Same structure as template but production-scale

**When to use:** Need production-ready patterns and complex gateway examples

**Key files to study:**
- `agent/agent_config/tools/research_tools.py` - Local tool patterns
- `prerequisite/lambda-database/python/database.py` - Gateway tools
- `README.md` - Production deployment workflow

### Additional References

**multi_agent_collaboration/cancer_biomarker_discovery/strands_agentcore/**
- Multiple specialized agents working together
- Agent collaboration patterns

**agents_catalog/17-variant-interpreter-agent/advanced-strands-agentcore/**
- Genomics pipeline integration
- AWS HealthOmics integration

## Troubleshooting

### Agent Not Responding
**Solutions:**
1. Check CloudWatch logs for errors
2. Verify tool execution completes
3. Test memory retrieval independently
4. Check Bedrock model availability

### Tool Selection Issues
**Solutions:**
1. Improve tool docstrings with examples
2. Add more specific tool descriptions
3. Enhance system prompt with tool usage guidelines

### Memory Not Persisting
**Solutions:**
1. Verify memory resource exists
2. Check actor_id and session_id consistency
3. Test memory operations independently

### Authentication Failures
**Solutions:**
1. Verify JWT token is valid
2. Check IAM role permissions
3. Review Cognito configuration

## Next Steps

### Recommended Workflow

1. **Read the Template README** - Navigate to `agentcore_template/README.md`
2. **Deploy the Template** - Follow step-by-step to deploy all components
3. **Study the Reference** - Review `agents_catalog/28-Research-agent-biomni-gateway-tools/`
4. **Build Your Agent** - Copy template structure and add your tools
5. **Scale and Optimize** - Apply production patterns from reference agent

### Quick Reference

**Starting point:** `agentcore_template/`
**Production reference:** `agents_catalog/28-Research-agent-biomni-gateway-tools/`
**Follow their READMEs:** Both provide complete step-by-step instructions

**Remember:** Start simple, test thoroughly, and progressively add complexity!

## Additional Resources

### Documentation
- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [Strands Framework Documentation](https://strandsagents.com/)
- [AWS HCLS Agent Repository](https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences)

### MCP Servers
- Use AgentCore MCP server to search AgentCore docs
- Use Strands MCP server to search Strands docs

### Community
- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share experiences
- Contributing: See CONTRIBUTING.md for guidelines

---

**Repository:** [amazon-bedrock-agents-healthcare-lifesciences](https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences)

**License:** MIT-0

**Important:** This is for demonstrative purposes only. Not for clinical use. Ensure HIPAA compliance and AWS BAA for PHI.
