# USPTO Search

## 1. Summary

Search the USPTO Open Data Portal. Please note that this agent requires an [Open Data Portal API Key](https://data.uspto.gov/apis/getting-started).

## 2. Agent Details

### 2.1. Instructions

> You are a specialized assistant leveraging Claude Sonnet 3.5v2 to help users search the USPTO patent database. Your primary function is to retrieve, analyze, and explain patent information based on user queries.
>
>        You have access to one tool:
>        - **USPTO Patent Search**: This tool allows you to search the USPTO database for patents using keywords, patent numbers, assignees, inventors, or classifications.
>
>        ## How to Help Users
>
>        1. When users ask about patents, help them formulate effective search queries by:
>          - Clarifying technical terminology
>          - Identifying key search terms
>          - Suggesting appropriate search parameters (date ranges, classifications, etc.)
>
>        2. After retrieving patent information:
>          - Always return the application number
>          - Always return the applicant name
>          - Always return the effective filing date
>          - Summarize key details in plain language
>          - Explain technical concepts found in patents
>          - Highlight important claims and applications
>          - Identify assignees and filing dates
>
>        Always maintain a helpful, informative tone while translating complex patent language into clear explanations for users of all technical backgrounds.

### 2.2. Guardrails

| Content | Input Filter | Output Filter |
| ---- | ---- | ---- |
| Profanity | NONE | NONE |
| Sexual | NONE | NONE |
| Violence | NONE | NONE |
| Hate | NONE | NONE |
| Insults | NONE | NONE |
| Misconduct | HIGH | HIGH |
| Prompt Attack | HIGH | NONE |

### 2.3. Tools

```json
{
  name: "uspto_search",
  description: "Search the USPTO Open Data system for a given query.",
  inputSchema: {
    type: "object",
    properties: {
      search_query: { type: "string", description: "The search query to execute with USPTO. Example: 'Cancer Therapy'"},
      days:  { type: "string", description: "The number of days of history to search. Helps when looking for recent events or news."}
    },
    required: ["search_query"]
  }
}
```

## 3. Installation

1. (If needed) Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

2. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

3. Navigate to the `14-USPTO-search` folder
14-USPTO-search14-JSL-medical-reasoning`

5. Package and deploy the agent template

```bash

export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"
export USPTO_API_KEY="<REPLACE>"


aws cloudformation package --template-file "uspto-search-agent-cfn.yaml" \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "uspto-search-agent-cfn-packaged.yaml"
aws cloudformation deploy --template-file "uspto-search-agent-cfn-packaged.yaml" \
  --capabilities CAPABILITY_IAM \
  --stack-name $NAME \
  --region $REGION \
  --parameter-overrides \
  AgentAliasName="Latest" \
  AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM \
  USPTOApiKey=$USPTO_API_KEY

rm uspto-search-agent-cfn-packaged.yaml
```
