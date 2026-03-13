# Claude for Life Sciences on Amazon Bedrock AgentCore

## Summary

Basic example of using skills and connectors from Claude for Life Sciences (C4LS) open source repository at <https://github.com/anthropics/life-sciences>.

## Skills

This example includes the following C4LS skills (defined in src/skills folder):

- [Instrument Data to Allotrope](https://github.com/anthropics/life-sciences/tree/main/instrument-data-to-allotrope)
- [Scientific Problem Selection](https://github.com/anthropics/life-sciences/tree/main/scientific-problem-selection)

## Connectors

This example includes the following connectors:

- [Open Target](https://github.com/anthropics/life-sciences/tree/main/open-targets/.claude-plugin)
- [PubMed](https://github.com/anthropics/life-sciences/tree/main/pubmed/.claude-plugin)

## Deployment

### Prerequisities

Install uv

```bash
uv curl -LsSf <https://astral.sh/uv/install.sh> | sh
uv --version
```

### Deployment Steps

1. `cd agents_catalog/36-C4LS-example-agent/C4LS`
1. `uv sync`
1. `uv run --with bedrock-agentcore-starter-toolkit agentcore configure`
1. `uv run --with bedrock-agentcore-starter-toolkit agentcore deploy`
1. `uv run --with bedrock-agentcore-starter-toolkit invoke agentcore invoke "What skills and tools do you have available?"`
