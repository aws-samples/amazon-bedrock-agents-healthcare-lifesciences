# Data Harmonisation for Drug Development Pipeline

This solution automatically collects, standardises, and enriches drug development pipeline data from pharmaceutical companies.

## Problem Statement

Harmonising data from disparate systems is time-consuming and costly. Pharmaceutical companies publish their drug/product development pipelines on their websites, but analyzing this data systematically presents several challenges:

- Manual downloading is often required
- Each company reports data in their own format
- Key data fields (indication, compound name, etc.) are reported inconsistently
- No standardized ontologies or controlled vocabularies are applied

An automated solution that retrieves, extracts, compiles to a common data model, and standardises with ontologies is essential to make the data FAIR (Findable, Accessible, Interoperable, Reusable) and ready for upstream analysis.

## Sample Questions
- "What diabetes drug candidates are in Phase 1 development?"
- "Compare the pipeline strategies of Novo Nordisk vs Pfizer"
- "Which compounds have Fast Track designation?"
- "Show me all biologics targeting oncology indications"
- "Analyze the distribution of development phases across therapeutic areas"

## Solution Overview

This notebook demonstrates how to extract and process pharmaceutical pipeline data using Q CLI and a simple prompt. This solution respects `robots.txt` directives and only collects data from websites that permit it.

### Step 1: Data Collection
Using Fetch MCP to collect data from Novartis, Novo Nordisk, and Pfizer pipeline web pages, extracting the data and saving it as individual JSON objects.

### Step 2: Common Data Model Creation
Analyzing each JSON file to create a unified data model that represents all collected data. This step combines data from the three companies into a single dataset.

### Step 3: Data Standardisation and Enrichment
Automatically detecting appropriate ontologies to standardize the data, ensuring consistency across all entries.

The final data is saved as a JSON file, ready for downstream analysis.

For implementation details, please see `./pipeline_data/PROJECT_SUMMARY.md`.

This folder was generated entirely using Q CLI.

### Step 4: Create RAG application and and Agent
Using CloudFormation template, this steps deploys Amazon Bedrock Agent that has a Knowledgebase. The Knowledgebase allows to ask questions about the drug development pipeline from the harmonised data in `enriched_pipeline_data.json`

## Deployment

The solution deployment automation script uses two parameterized CloudFormation template, 01-deploy-oass.yml and 02-deploy-kb-agent.yml, to automate provisioning of following solution resources:
- OpenSearch Service Serverless collection
- Amazon S3 Bucket (DataSource)
- Amazon Bedrock KnowledgeBase
- Amazon Bedrock Agent
- IAM Roles

There are two stacks to deploy

### Deploy 01-deploy-oass.yaml

1. You need to add the ARN of the IAM role with which you are currently logged into your AWS account. 

`cloudformation create-stack --stack-name <stack-name> --template-body 01-deploy-oass.yaml --parameters ParameterKey=<parameter key>,ParameterValue=<parameter value> ParameterKey=<parameter key>,ParameterValue=<parameter value> `

2. After the stack is deployed, go to 'Outputs' tab and make a note of the output fields highlighted below

3. Go to AWS Consle 
	1. Go to S3 and upload `enriched_pipeline_data.json` to your bucket. You can find your bucket name marked as 1 in the image above
	`aws s3 sync /<your dir>/pipeline_data/final_enriched_data/enriched_pipeline_data.json s3://$BUCKET_NAME/`
	2. Go to Amazon OpenSearch Serverless
		- Collections
		- Find `pipeline-rag`
		- `Create index`
			- Index name: `rag-pipeline-readthedocs-io`
			- Vector field name: `vector`
			- Engine: `faiss`
			- Precision: `FP16`
			- Dimensions: `1536`
			- Distance metric: `Euclidean`

### Deploy 02-agent-with-kb.yaml
You can either use the AWS Console or AWS CLI

`aws cloudformation create-stack --stack-name <stack-name> --template-body file://02-agent-with-kb.yaml --parameters ParameterKey=<parameter key>,ParameterValue=<parameter value> ParameterKey=<parameter key>,ParameterValue=<parameter value>` 

Fill the following fields
- Stack name: name of your choice e.g. `data-harmonisation-agent`
- AmazonBedrockExecutionRoleForKnowledgeBasearn: you can find it in the Output section of the first stack, as shown in the image above
- CollectionArn: same as above
- DataSource: same as above
- S3bucketarn: same as above

