# Create a Omics Signatures Enrichment Agent

Create an end-to-end Omics metadata mapping solution, integrated with [Reactome](https://reactome.org/) database to retrieve identifiers from external databases.

## Sample Database Overview

This example utilizes the reactome database, a biological pathway database commonly used for pharmaceutical research purposes. 

### Use Case: Pharmaceutical research agent

Pharmaceutical researchers can interact with Reactome's biological pathway database to enrich metadata related to genes, proteins, molecules and signalling pathways through natural language queries.

Here are some example questions that can be answered by this agent.

    * Tell me more about LRIG1 ? 
    * Provide the primary name, alternative name, literature references and key identifiers in external databases for the gene LRIg1 ?
    * Provide the primary name, alternative name, and key identifiers in external databases for Signaling by EGFR in Cancer (R-HSA-1643713)

This Text-to-Cypher solution enables researchers to perform:

- Metadata mapping with external databases 
- External identifiers with literature
- Understand constituent events of signaling pathways

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

1. User asks questions to the agent.
2. To serve the user's questions, Agent determines the appropriate action to invoke.
3. It will invoke the lambda function and execute the /getschema action to retrieve the portion of the schema relevant to the user question.
4. The agent will use the retrieved schema to generate an OpenCypher query.a
5. The generated query will be used as the parameter to the /queryneptune action to query the Neptune database with the given query.
6. The lambda function will return the query results, which the agent will use to generate the natural language answer.

## Getting Started

### Prerequisites 
**NOTE**: (You can skip if already executed with the Biological pathways analyst agent)

- Deploy the 'text2cypher_infra.yaml' file provided in the folder using your AWS account's CloudFormation service to deploy the Neptune database and the S3 buckets
- Enable model access to all Bedrock models from the AWS console
- Create a SageMaker notebook instance in your AWS account (NOTE: MAKE SURE THE SAGEMAKER NOTEBOOK INSTANCE IS PLACED IN THE SAME VPC AS THE NEPTUNE DATABASE THAT WAS CREATED THROUGH THE YAML FILE)
- Look at the image below for reference:

![SageMaker Notebook Config](../images/sagemaker_notebook_config.png) 



### Deployment

Step 1: Navigate to agents_catalog/0-Notebook-environment/ and go to setup_environment.ipynb, use the Python 3 (ipykernel)

Step 2: Run through the 'sample_text2cypher_agent.ipynb' to create the Text-to-Cypher agent

## How to Test in AWS Console

1. Go to [Amazon Bedrock](https://console.aws.amazon.com/bedrock) and select **Agents.**

2. Select your Text-to-Cypher agent and test by asking questions in **Test** window on your right. 

## License

- [MIT-0](/LICENSE)
