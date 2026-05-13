---
name: hcls-build-agent
description: Use when a developer wants to build a new healthcare or life sciences agent, structure tools and system prompts for an HCLS workflow, or create a Strands agent with domain-specific capabilities. Also use when someone asks about agent architecture, tool design, or system prompt patterns for clinical, genomics, or drug discovery use cases.
---

# Building an HCLS Agent

## When to use this skill

- Developer asks "how do I create a new HCLS agent?"
- Developer needs to structure tools, prompts, and workflows for a healthcare domain
- Developer is building an agent for genomics, drug discovery, clinical trials, or other HCLS workflows

## Agent Architecture

An HCLS agent is composed of:

```
Agent = System Prompt + Tools (MCP) + Skills (Knowledge) + Guardrails
```

## Steps

### 1. Choose a template

| Template | When to use |
|----------|------------|
| `agentcore_template/` | Backend-focused: agent runtime + Gateway tools + Streamlit UI |
| [FAST](https://github.com/awslabs/fullstack-solution-template-for-agentcore) | Full-stack: React frontend + Cognito auth + CDK deployment |

### 2. Define your agent's domain scope

- What HCLS workflow does it address?
- What data sources does it need? (databases, ontologies, literature)
- What actions should it perform? (query, analyze, generate, validate)
- What guardrails are needed? (PHI handling, clinical disclaimers, data validation)

### 3. Create tools

Tools are Python functions exposed via AgentCore Gateway (Lambda targets) or as local Strands tools.

```python
# Local Strands tool
from strands import tool

@tool
def search_variants(gene: str, significance: str = "pathogenic") -> dict:
    """Search for genetic variants by gene name and clinical significance."""
    # Implementation
    pass
```

For Gateway tools (accessible to any MCP client), create Lambda functions and register as Gateway targets. See `agents_catalog/28-Research-agent-biomni-gateway-tools/` for the pattern.

### 4. Write the system prompt

Include:
- Domain expertise and role definition
- Available tools and when to use each
- Output format expectations
- Clinical/scientific disclaimers
- Guardrails (what NOT to do)

### 5. Add MCP server connections

Reference existing MCP servers for domain tools the agent needs:
- Biomedical databases: deploy Biomni Gateway (`mcp-servers/agentcore-gateway/biomni-research-tools/`)
- Ontology lookup: deploy OLS server (`mcp-servers/agentcore-runtime/ontology-lookup-service/`)
- Literature: configure PubMed (`mcp-servers/third-party/pubmed/`)
- Genomics workflows: configure HealthOmics (`mcp-servers/aws-public/aws-healthomics/`)

### 6. Test

```bash
# Local testing with Strands
python main.py --prompt "Your test query"

# Test Gateway tools independently
python tests/test_gateway.py --prompt "Your test query"
```

## References

- Reference implementation (simple): `agents_catalog/24-Deep-Research-agent/`
- Reference implementation (full Gateway): `agents_catalog/28-Research-agent-biomni-gateway-tools/`
- Reference implementation (FAST template): `agents_catalog/35-Terminology-agent/`
- Strands Agents docs: use the `strands-docs` MCP server
- AgentCore docs: use the `agentcore-docs` MCP server

## AWS MCP Servers Used

When building infrastructure for the agent, use:
- `aws-mcp` — create IAM roles, Lambda functions, S3 buckets
- `agentcore-docs` — AgentCore API reference for Gateway/Runtime/Memory configuration
- `aws-healthomics` — if the agent needs genomics workflow capabilities
