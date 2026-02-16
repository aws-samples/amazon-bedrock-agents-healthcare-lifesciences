# HCLS AgentCore Builder Power

A comprehensive Kiro Power for building production-ready Healthcare and Life Sciences AI agents using Amazon Bedrock AgentCore and Strands framework.

## What This Power Does

This power guides developers through building their first AgentCore agent with:
- Step-by-step workflows from POC to production
- Best practices for production-ready agentic AI systems
- Agent patterns for HCLS use cases
- Integration with AgentCore and Strands MCP servers
- Reference to repository steering files and examples

## Target Audience

Developers building AI agents for healthcare and life sciences workflows:
- Drug research and discovery
- Clinical trials and protocol generation
- Biomarker analysis
- Medical imaging and pathology
- Regulatory compliance

## Key Features

### Primary References
- **agentcore_template/** - Complete starting point for new agents
- **agents_catalog/28-Research-agent-biomni-gateway-tools/** - Production reference with 30+ tools

### Comprehensive Guidance
- 6-stage deployment workflow (POC → Memory → Gateway → Security → Production → Observability)
- Agent patterns (RAG, Tool-Based, Workflow Orchestration, Multi-Agent)
- LLM workflow patterns (Prompt Chaining, Routing, Parallelization, Orchestration)
- Best practices from AWS documentation
- Common pitfalls and solutions
- Success criteria and metrics

### Integration
- Works with AgentCore MCP server for documentation
- Works with Strands MCP server for framework docs
- Includes steering files with repository knowledge (product.md, structure.md, tech.md)

## Installation

### Option 1: Local Directory (Development)

1. Ensure this power directory is in your workspace at `powers/hcls-agentcore-builder/`
2. Open Kiro Powers UI
3. Click "Add Custom Power"
4. Select "Local Directory"
5. Enter the full path to this directory
6. Click "Add"

### Option 2: Git Repository (Sharing)

If you want to share this power via GitHub:

1. Create a public GitHub repository
2. Copy this power directory to the repository root
3. Push to GitHub
4. Users can add via Powers UI using the repository URL

## Usage

Once installed, activate the power in Kiro:

```
Activate power: hcls-agentcore-builder
```

The power provides:
- Complete documentation in POWER.md
- Three steering files with repository knowledge (product, structure, tech)
- References to template and example agents
- Step-by-step deployment workflows
- Best practices and patterns
- Troubleshooting guidance

**Access steering files:**
```
Read steering file: product.md (repository overview)
Read steering file: structure.md (project structure)
Read steering file: tech.md (technology stack)
```

## Prerequisites

Users of this power should have:
- AWS account with Bedrock access
- Python 3.10+
- AWS CLI configured
- Basic understanding of AWS services
- Familiarity with Python and REST APIs

## Repository Structure

This power is designed for the [amazon-bedrock-agents-healthcare-lifesciences](https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences) repository.

Key references:
- `agentcore_template/` - Starting point for new agents
- `agents_catalog/28-Research-agent-biomni-gateway-tools/` - Production reference
- `.kiro/steering/` - Technology stack and architecture guidance

## MCP Servers

This power works with:
- **power-aws-agentcore-agentcore-mcp-server** - AgentCore documentation
- **power-strands-strands-agents** - Strands framework documentation

## Contributing

To improve this power:
1. Update POWER.md with new best practices or patterns
2. Add examples from new agents in the catalog
3. Update troubleshooting section with common issues
4. Keep references to template and example agents current

## License

This power is part of the amazon-bedrock-agents-healthcare-lifesciences repository and follows the MIT-0 License.

## Important Notes

- For demonstrative purposes only - not for clinical use
- Not a substitute for professional medical advice
- Ensure HIPAA compliance if handling PHI
- Requires AWS Business Associate Addendum (BAA) for PHI

## Support

For issues or questions:
- GitHub Issues: [amazon-bedrock-agents-healthcare-lifesciences](https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences/issues)
- Follow the template and reference agent READMEs
- Use MCP servers for documentation lookup
