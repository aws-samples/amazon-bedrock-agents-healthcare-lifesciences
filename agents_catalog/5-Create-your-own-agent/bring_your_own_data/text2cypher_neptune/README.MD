# Create a Text2Cypher Bedrock Agent

Create an end-to-end Text-to-Cypher solution, integrated with Neptune database.

## Sample Database Overview

This example utilizes the reactome database, a biological pathway database commonly used for pharmaceutical research purposes. 

### Use Case: Pharmaceutical research agent

Pharmaceutical researchers can interact with Reactome's biological pathway database to explore complex disease mechanisms, drug interactions, and therapeutic targets through natural language queries.

Here are some example questions that can be answered by this agent.

    * What are the immediate downstream reactions that are triggered by EGFRvIII in the 'Signaling by EGFRvIII in Cancer (R-HSA-5637812)' pathway in Homo sapiens? 
    * "What proteins are associated with Signaling by EGFR in Cancer (R-HSA-1643713)?"
    * Which chemical compounds are involved in Mitochondrial translation termination (R-HSA-5419276)?

This Text-to-Cypher solution enables researchers to perform:

- Pathway Analysis 
- Drug target discovery
- Disease Mechanism Investigation

### Workflow of the Text2Cypher Agent

1. **Schema Discovery**
    - Retrieves the schema for the specified Neptune database
    - Truncates the retrieved schema to only include parts of the schema relevant to the user question.
    - Returns schema information including node names, node types, relationships, and their types.

2. **Natural Language Query Processing**
    - Converts natural language questions into OpenCypher queries
    - Executes queries against Amazon Neptune
    - Returns results in user-friendly format

### Agentic Text2Cypher Flow

1. User asks questions to the Amazon Bedrock Agent.
2. To serve the user's questions, Agent determines the appropriate action to invoke.
3. It will invoke the lambda function and execute the /getschema action to retrieve the portion of the schema relevant to the user question.
4. The agent will use the retrieved schema to generate an OpenCypher query.a
5. The generated query will be used as the parameter to the /queryneptune action to query the Neptune database with the given query.
6. The lambda function will return the query results, which the agent will use to generate the natural language answer.

## Getting Started

### Prerequisites

- Deploy the 'text2cypher_infra.yaml' file provided in the folder using your AWS account's CloudFormation service to deploy the Neptune database and the S3 buckets
- Create a SageMaker notebook instance in your AWS account (NOTE: MAKE SURE THE SAGEMAKER NOTEBOOK INSTANCE IS PLACED IN THE SAME VPC AS THE NEPTUNE DATABASE THAT WAS CREATED THROUGH THE YAML FILE)
- Enable model access to all Bedrock models from the AWS console

### Deployment

Step 1: Go to a SageMaker Notebook instance in your AWS account and clone this repository in a terminal

```bash
cd SageMaker/
git clone https://github.com/aws-samples/amazon-bedrock-agents-cancer-biomarker-discovery.git
```

Step 2: Navigate to the multi-agent-collaboration branch within the repository
```bash
cd amazon-bedrock-agents-cancer-biomarker-discovery
```
```bash
git checkout multi-agent-collaboration
```

Step 3: Navigate to agents_catalog/0-Notebook-environment/ and go to setup_environment.ipynb, use the Python 3 (ipykernel)

Step 4: Run through the 'sample_text2cypher_agent.ipynb' to create the Text-to-Cypher agent

## How to Test in AWS Console

1. Go to [Amazon Bedrock](https://console.aws.amazon.com/bedrock) and select **Agents.**

2. Select your Text-to-Cypher agent and test by asking questions in **Test** window on your right. 

    Example questions:

    * What are the immediate downstream reactions that are triggered by EGFRvIII in the 'Signaling by EGFRvIII in Cancer (R-HSA-5637812)' pathway in Homo sapiens? 
    * "What proteins are associated with Signaling by EGFR in Cancer (R-HSA-1643713)?"
    * Which chemical compounds are involved in Mitochondrial translation termination (R-HSA-5419276)?
    * 'What are 5 different types of proteins involved with the SARS-CoV-2 Infection (R-HSA-9694516)?'
    * According to the Reactome database, which molecules participate in Interleukin-4 and Interleukin-13 signaling?
    * According to the Reactome database, which events are in the Cap-dependent Translation Initiation pathway?

3. Click Show trace and examine each step to understand what tools are used and the agent's rationale for approaching your question.

## License

- [MIT-0](/LICENSE)