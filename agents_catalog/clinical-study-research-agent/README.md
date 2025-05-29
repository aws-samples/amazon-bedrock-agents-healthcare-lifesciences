# Clinical Study Research Agent

This agent helps users explore, filter, and analyze clinical trial data from public registries like ClinicalTrials.gov. It assists with condition-specific study identification, intervention tracking, sponsor profiling, and outcome analysis using structured search criteria.

## Features

- **Clinical Study Search**: Search for clinical trials based on conditions, interventions, outcomes, and other parameters
- **Trial Details**: Get comprehensive information about specific clinical trials
- **Data Visualization**: Create charts and visualizations of clinical trial data
- **Drug Information**: Retrieve information about approved drugs for specific conditions

## Architecture

The agent consists of three main Lambda functions:

1. **Clinical Study Search Lambda**: Handles searching and retrieving clinical trial data
2. **Clinical Visualizer Lambda**: Creates visualizations of clinical trial data
3. **Drug Information Lambda**: Retrieves information about approved drugs

## Deployment

The agent is deployed using AWS CloudFormation. The template creates all necessary resources including:

- Amazon Bedrock Agent with action groups
- Lambda functions and layers
- IAM roles and permissions
- S3 bucket for storing chart images
- Guardrail for content filtering

### Prerequisites

- AWS CLI configured with appropriate permissions
- Amazon Bedrock access
- IAM role for the Bedrock agent

### Deployment Steps

1. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

2. Navigate to the `15-clinical-study-research-agent` folder.

`cd 15-clinical-study-research-agent`

```bash
export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"
export IMAGE_BUCKET="<REPLACE>"

bash deploy.sh
```

## Usage Examples

### Search for Clinical Trials

"Find clinical trials for diabetes using GLP-1 agonists that measure HbA1c reduction compared to placebo"

### Get Trial Details

"Show me details for clinical trial NCT04000165"

### Create Visualizations

"Create a pie chart showing the distribution of diabetes trials by phase"

### Get Drug Information

"What drugs are approved for type 2 diabetes with oral administration?"

## Customization

You can customize the agent by:

1. Modifying the Lambda function code in the action_groups directory
2. Updating the agent instructions in the CloudFormation template
3. Adding additional action groups for new functionality
