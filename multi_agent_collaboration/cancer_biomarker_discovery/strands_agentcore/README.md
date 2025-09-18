# Cancer Biomarker Discovery with Strands Agents And Bedrock AgentCore

This implementation demonstrates how to replicate the cancer biomarker discovery multi-agent system using Strands agents and deployment with Amazon Bedrock AgentCore.

## Architecture Overview

![architecture](../images/Biomarker_agents_Strands_AgentCore.png)

The **Strands Orchestrator Agent** implements the [Agent as Tools](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agents-as-tools/) concept proposed by Strands Agents framework by defining the specialized agents below as tools.

## Specialized Agents

### 1. Biomarker Database Analyst
- **Tools**: `get_database_schema`, `query_biomarker_database`, `refine_sql_query`
- **Capabilities**: SQL generation, database queries, schema analysis

### 2. Clinical Evidence Researcher
- **Tools**: `search_pubmed`
- **Capabilities**: Literature search, evidence synthesis, citation analysis

### 3. Medical Imaging Expert
- **Tools**: `process_medical_images`
- **Capabilities**: Image processing, radiomics analysis, biomarker extraction

### 4. Statistician Agent  
- **Tools**: `perform_survival_analysis`, `create_bar_chart`
- **Capabilities**: Survival analysis, statistical modeling, data visualization

## Prerequisites

1. These notebooks were designed to run with Amazon SageMaker Studio. To use Studio, you will need to setup a SageMaker Domain. For instructions on how to onboard to a Sagemaker domain, refer to this [link](https://docs.aws.amazon.com/sagemaker/latest/dg/gs-studio-onboard.html).

2. With the SageMaker domain created, you have to create a **JupyterLab space**. We recommend an instance size of **ml.t3.large** and at least **50 GB** of storage.

3. If you are running the notebooks locally, make sure you have the [AWS CLI](https://aws.amazon.com/cli/) installed in your environment.

## Setup Instructions

You have two options to run these samples: deploying the existing cloud formation template in an AWS account or running the notebooks to create the agents one by one and manually deploying them on Bedrock AgentCore.

### 1. Deploy Infrastructure

Run the following command to deploy all the infrastructure components needed for the agents:

```bash
# Deploy the original CloudFormation stack (no changes needed)
aws cloudformation deploy --template-file agent_build.yaml --stack-name biomarker-agents
```
Execute notebook [05-multi_agent_biomarker_strands](05-multi_agent_biomarker_strands.ipynb) to create the orchestrator agent and deploy it on Bedrock AgentCore.

### 2. Notebooks

The sample notebooks you will explore how agentic workflows powered by [Strands Agents](https://strandsagents.com/latest/) framework and large language models on Amazon Bedrock can enhance complex oncology research. You will learn how AI-driven agents leverage planning, tool-use, and self-reflection to transform intricate research queries into actionable insights. You will also learn how to deploying the agents on [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) Runtime.

1. Clone this repository or manually import all files from this project into your JupyterLab workspace.
2. To setup the environment, first run notebook [00-setup_environment.ipynb](00-setup_environment.ipynb).
3. Notebooks 1 to 5 are typically executed in order, but you can also run them independently.
4. Follow the instructions on each notebook to run the cells. Some of the notebooks will have a Setup section in the beginning with additional installation instructions.

### 3. User Interface

We also provide a Streamlit UI that can be used as a front end for your agents. To execute the UI locally, you'll need to install Streamlit on your local Python environent. You can do that by running the following command (assuming you are running from the folder where this README is located):

```bash
pip install -r ui/requirements.txt
```

To run the Streamlit application, execute the following command from the same path:

```bash
streamlit run ui/app.py -- --env env1
```

The Streamlit application will load on your default web browser and it typically runs on ```http://localhost:8501/```