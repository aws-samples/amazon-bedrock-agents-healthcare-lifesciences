# Product Overview

This is a sample repository for Healthcare and Life Sciences (HCLS) AI agents built on AWS, specifically using Amazon Bedrock AgentCore and the Strands framework.

## Purpose

Provides a comprehensive toolkit for building specialized AI agents for healthcare and life sciences workflows including:
- Drug research and discovery
- Clinical trials and protocol generation
- Biomarker analysis
- Medical imaging and pathology
- Regulatory compliance (SEC, USPTO, FDA)
- Scientific literature research

## Key Components

- **agentcore_template**: End-to-end template for deploying agents with Bedrock AgentCore (Runtime, Gateway, Identity, Memory, Observability) and Streamlit UI
- **agents_catalog**: Library of 30+ specialized agents for common HCLS workflows
- **multi_agent_collaboration**: Framework for multi-agent systems working together
- **evaluations**: Methods for assessing agent performance
- **ui**: React-based web interface for agent interaction

## Recommended Deployment Approach (v2)

**Use this for all new agent development:**
- **Amazon Bedrock AgentCore** for agent infrastructure
- **Strands agents framework** for agent development
- CloudFormation for infrastructure as code
- Streamlit or React for user interfaces

Refer to `agentcore_template/` for the reference implementation.

## Legacy Approach (v1 - Deprecated)

**⚠️ Note:** Many agents in the catalog still use the deprecated **Bedrock Agents** approach from v1. These are maintained for reference but should NOT be used as templates for new development.

- If you see agents using `AWS::Bedrock::Agent` resources in CloudFormation, these are v1 legacy agents
- Some CloudFormation templates in `Infra_cfn.yaml` and individual agent stacks still reference Bedrock Agents
- **Do not use these as starting points** - always start with `agentcore_template/` for new agents

## Important Notes

- This is for **demonstrative purposes only** - not for clinical use
- Not a substitute for professional medical advice
- Customers must ensure HIPAA compliance if handling protected health information
- Must enter AWS Business Associate Addendum (BAA) before using with PHI
