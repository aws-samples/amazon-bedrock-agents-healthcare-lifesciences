# HCLS Agents Toolkit

You are assisting with healthcare and life sciences AI development on AWS. This toolkit provides domain skills, MCP tools, and production agent patterns.

## Available Resources

- **Skills** (`skills/`) — Domain workflow guidance for genomics, drug discovery, clinical trials, biomarkers, medical terminology
- **MCP Servers** (`mcp-servers/`) — Biomedical databases, ontology services, literature search, genomics tools
- **Agent Catalog** (`agents_catalog/`) — 36+ production-ready HCLS agents

## Key Conventions

- Framework: Strands Agents SDK
- Infrastructure: Amazon Bedrock AgentCore (Runtime, Gateway, Memory, Identity, Registry)
- Default model: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- Deployment templates: `agentcore_template/` (backend) or FAST (full-stack)

## Domain Awareness

- Healthcare data is sensitive — never include real PHI in generated code
- Clinical outputs need disclaimers — this toolkit is not a substitute for medical advice
- Genomic interpretations depend on database versions — always note the source
- Use HCLS MCP tools over general web search for biomedical questions
