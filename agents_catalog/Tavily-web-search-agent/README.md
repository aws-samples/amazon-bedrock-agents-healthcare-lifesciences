# Tavily Web Search Agent

## 1. Summary

Answer questions using up-to-date information retrieved by the [Tavily Search API](https://tavily.com/).

## 2. Installation

1. Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

1. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

1. Navigate to the `Tavily-web-search-agent` folder

`cd agents_catalog/Tavily-web-search-agent`

1. Package and deploy the agent template

```bash
export BUCKET_NAME="<REPLACE>"
export STACK_NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"

aws cloudformation package --template-file agents_catalog/Tavily-web-search-agent/web-search-agent-cfn.yaml \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "agents_catalog/Tavily-web-search-agent/packaged-web-search-agent-cfn.yaml"
aws cloudformation deploy --template-file agents_catalog/Tavily-web-search-agent/packaged-web-search-agent-cfn.yaml \
  --capabilities CAPABILITY_IAM \
  --stack-name $STACK_NAME \
  --region $REGION \
  --parameter-overrides AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM TavilyApiKey="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"
rm agents_catalog/Tavily-web-search-agent/packaged-web-search-agent-cfn.yaml
```
