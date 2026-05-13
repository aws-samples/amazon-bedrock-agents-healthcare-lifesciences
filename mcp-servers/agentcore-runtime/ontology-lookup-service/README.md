# Ontology Lookup Service — AgentCore Runtime

MCP server providing medical and biological terminology standardization using the EBI Ontology Lookup Service (OLS), supporting 200+ ontologies including MONDO, ChEBI, HPO, GO, SNOMED, and more.

## Tools Available

- Search terms across ontologies
- Look up specific ontology entries
- Map between ontology systems
- Extract entities from text and standardize against ontologies
- Browse ontology hierarchies

## Deployment

This server reuses the deployment from [Agent 35 (Terminology Agent)](../../../agents_catalog/35-Terminology-agent/).

The Terminology Agent is built on the [FAST template](https://github.com/awslabs/fullstack-solution-template-for-agentcore) and includes the OLS MCP server as a custom tool deployed to AgentCore Runtime.

**Follow the Agent 35 README for deployment instructions.**

## Connecting Your AI Assistant

After deployment, the MCP server is accessible via the AgentCore Runtime endpoint. See the Agent 35 README for connection details.

## Source

- Full implementation: [agents_catalog/35-Terminology-agent/](../../../agents_catalog/35-Terminology-agent/)
- External API: [EBI Ontology Lookup Service](https://www.ebi.ac.uk/ols4/)
