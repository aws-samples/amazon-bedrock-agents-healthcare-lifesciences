# HCP Mock Intelligence Agent

## 1. Summary

Generate mock healthcare provider information, similar to that provided by a HCP CRM or other engagement database.

## 2. Agent Details

### 2.1. Instructions

> Analyze the available data for the specified healthcare provider to develop a personalized engagement strategy. > > Follow these steps:
>
> 1. Gather and synthesize data from all available sources:
>
> * Content preferences (delivery channels, topics, formats)
> * Historical engagement metrics (email opens, content views, meeting patterns)
> * CRM interaction notes and information requests
> * Public professional activities (publications, social media presence, speaking engagements)
>
> 2. Identify key patterns and insights:
>
> * Preferred communication channels and timing
> * High-engagement topics and content formats
> * Professional interests and focus areas
> * Gaps in current engagement approach
>
> 3. Develop a tailored engagement plan including:
>
> * Recommended content topics and formats
> * Optimal communication channels and frequency
> * Specific engagement opportunities based on the HCP's interests
> * Measurable success metrics for the proposed strategy
>
> Present your analysis and recommendations in a structured format with clear rationale derived from the data.
> Highlight the most actionable insights that would meaningfully improve engagement with this HCP.

### 2.2. Guardrails

| Content | Input Filter | Output Filter |
| ---- | ---- | ---- |
| Profanity | HIGH | HIGH |
| Sexual | NONE | NONE |
| Violence | NONE | NONE |
| Hate | NONE | NONE |
| Insults | NONE | NONE |
| Misconduct | HIGH | HIGH |
| Prompt Attack | HIGH | NONE |

### 2.3. Tools

```json
{
  name: "get_mock_content_preferences",
  description: "Retrieve synthetic data that describes channel preference (digital vs face-to-face), content preference (video vs text vs interactive), and topics of interest for a given HCP.",
  inputSchema: {
    type: "object",
    properties: {
      full_name: { type: "string", description: "First and last name without any titles, e.g. Alejandro Rosalez, or John Stiles"},
    },
    required: ["full_name"]
  }
},
{
  name: "get_mock_engagement_data",
  description: "Retrieve synthetic engagement data for topics of interest, field interaction notes, and medical information requests.",
  inputSchema: {
    type: "object",
    properties: {
      full_name: { type: "string", description: "First and last name without any titles, e.g. Alejandro Rosalez, or John Stiles"},
    },
    required: ["full_name"]
  }
},
{
  name: "get_mock_public_profile",
  description: "Retrieve recent examples of scientific journal publications, news articles, and social media posts.",
  inputSchema: {
    type: "object",
    properties: {
      full_name: { type: "string", description: "First and last name without any titles, e.g. Alejandro Rosalez, or John Stiles"},
    },
    required: ["full_name"]
  }
}
```

## 3. Installation

1. (If needed) Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

2. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

3. Navigate to the `13-mock-hcp-intelligence-agent` folder

`cd agents_catalog/13-mock-hcp-intelligence-agent`

5. Package and deploy the agent template

```bash
export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"
aws s3 cp mock_hcp_data.json s3://$BUCKET_NAME/mock_hcp_data.json
aws cloudformation package --template-file "mock-hcp-intelligence-agent.yaml" \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "mock-hcp-intelligence-agent-packaged.yaml"
aws cloudformation deploy \
  --template-file "mock-hcp-intelligence-agent-packaged.yaml" \
  --stack-name $STACK_NAME --region $REGION --capabilities CAPABILITY_IAM \
  --parameter-overrides \
  AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM \
  S3BucketName=$BUCKET_NAME
rm "mock-hcp-intelligence-agent-packaged.yaml"
```
