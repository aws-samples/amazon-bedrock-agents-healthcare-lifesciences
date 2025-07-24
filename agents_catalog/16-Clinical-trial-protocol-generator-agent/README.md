# Clinical Trial Protocol Generator Agent

This agent helps users create, and optimize clinical trial protocols based on best practices and common data model (cdm). It assists with protocol design, inclusion/exclusion criteria development, endpoint selection, and statistical considerations.

## Features

- **Protocol Template Generation**: Create structured clinical trial protocol templates based on study type and phase
- **Protocol Review**: Analyze existing protocols for completeness, consistency, and regulatory compliance
- **Inclusion/Exclusion Criteria**: Generate and refine participant eligibility criteria
- **Endpoint Selection**: Recommend appropriate primary and secondary endpoints based on the condition and intervention
- **Statistical Planning**: Provide sample size calculations and statistical analysis plan recommendations

## Architecture

The agent consists of two main Lambda functions:

1. **Protocol Generator Lambda**: Handles the creation and review of clinical trial protocols
2. **Protocol Optimizer Lambda**: Provides recommendations for optimizing protocols based on best practices

## Deployment

The agent is deployed using AWS CloudFormation. The template creates all necessary resources including:

- Amazon Bedrock action groups
- Lambda functions and layers
- IAM roles and permissions
- Guardrail for content filtering

### Prerequisites

- AWS CLI configured with appropriate permissions
- Amazon Bedrock access
- IAM role for Bedrock

### Deployment Steps

1. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

2. Navigate to the `16-Clinical-trial-protocol-generator-agent` folder.

`cd 16-Clinical-trial-protocol-generator-agent`

```bash
export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"

bash deploy.sh
```

## Usage Examples

### Generate Protocol Template

"Create a Phase 2 protocol template for a randomized controlled trial testing a new GLP-1 agonist in type 2 diabetes"

### Review Protocol

"Review my protocol for completeness and regulatory compliance"

### Generate Inclusion/Exclusion Criteria

"Generate inclusion and exclusion criteria for a trial of a new antidepressant in adults with treatment-resistant depression"

### Recommend Endpoints

"What endpoints should I use for a Phase 3 trial of a new heart failure medication?"

### Statistical Planning

"Calculate the sample size needed for a superiority trial with 90% power to detect a 15% difference in response rate"

## Customization

You can customize the agent by:

1. Modifying the Lambda function code in the action_groups directory
2. Updating the agent instructions in the CloudFormation template
3. Adding additional action groups for new functionality
