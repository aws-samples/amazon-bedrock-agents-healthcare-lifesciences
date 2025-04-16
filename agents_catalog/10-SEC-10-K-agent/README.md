# SEC Form 10-K agent

## 1. Summary

Answer questions regarding company financial data reported on SEC 10-K forms.

## 2. Agent Details

### 2.1. Instructions

> You are an expert financial analyst specializing in public company analysis using SEC 10-K data. Help users analyze companies by retrieving and interpreting financial data through the SEC EDGAR API tools.
>
> You have access to the following tools:
>
> - find_relevant_tags: Find the most relevant SEC EDGAR database tags for a given query. May be used to identify the input values for the get_company_concept function.
> - get_company_concept: Retrieves us-gaap disclosures from the EDGAR API for a specified company and concept (tag), returning an array of facts organized by units of measure (such as profits in different currencies).
>
> You also have the ability to generate and run code. This could be useful for statistical analysis or data visualization.
>
> Analysis Process
>
> 1. Begin by asking which company the user wants to analyze, if not provided.
> 2. Use find_relevant_tags to determine which specific SEC EDGAR database tags are relevant based on the user's goals.
> 3. Use get_company_concept to retrieve targeted financial data.
> 4. Analyze trends, calculate financial ratios, and provide insights. Generate and run code as needed.
> 5. Present your analysis in a clear, structured format with relevant visualizations or tables.
>
> Response Guidelines
>
> - Provide concise, actionable insights based on the data
> - Explain financial concepts in accessible language
> - Include relevant metrics like revenue growth, profitability ratios, and balance sheet analysis
>   - Highlight notable trends or concerns
>   - Make appropriate comparisons to industry standards when possible
>   - Acknowledge data limitations and gaps where they exist

### 2.2. Guardrails

| Content | Input Filter | Output Filter |
| ---- | ---- | ---- |
| Profanity | HIGH | HIGH |
| Sexual | NONE | NONE |
| Violence | NONE | NONE |
| Hate | NONE | NONE |
| Insults | NONE | NONE |
| Misconduct | NONE | NONE |
| Prompt Attack | HIGH | NONE |

### 2.3. Tools

```json
{
  name: "find_relevant_tags",
  description: "Find the most relevant SEC tags for a given query. May be used to identify the input values to the get_company_concept function.",
  inputSchema: {
    type: "object",
    properties: {
      query: { type: "string", description: "Topic or question to search against all available SEC tags in the us-gaap taxonomy"},
    },
    required: ["query"]
  }
},
{
  name: "get_company_concept",
  description: "Get all the us-gaap disclosures for a single company (CIK) and concept (tag), with a separate array of facts for each unit of measure that the company has chosen to disclose (e.g. net profits reported in U.S. dollars and in Canadian dollars).",
  inputSchema: {
    type: "object",
    properties: {
      company_name: { type: "string", description: "Company name, e.g. Amazon or Pfizer"},
      tag: { type: "string", description: "An identifier that highlights specific information to EDGAR in the format required by the EDGAR Filer Manual. e.g. 'EntityCommonStockSharesOutstanding', 'AcceleratedShareRepurchasesFinalPricePaidPerShare'"},
    },
    required: ["company_name", "tag"]
  }
}
```

## 3. Installation

1. (If needed) Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

2. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

3. Navigate to the `SEC-10-K-agent` folder

`cd agents_catalog/SEC-10-K-agent`

4. Package and deploy the agent template

```bash
export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export S3CodeKey="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"

pushd action-groups/SEC-10-K-search/docker
zip -r docker.zip .
aws s3 cp docker.zip s3://$BUCKET_NAME/docker.zip
rm docker.zip
popd
aws cloudformation package --template-file "sec-10-K-agent-cfn.yaml" \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "sec-10-K-agent-cfn-packaged.yaml"
aws cloudformation deploy --template-file "sec-10-K-agent-cfn-packaged.yaml" \
  --capabilities CAPABILITY_IAM \
  --stack-name $NAME \
  --region $REGION \
  --parameter-overrides \
  AgentAliasName="Latest" \
  AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM \
  S3CodeBucket=$BUCKET_NAME \
  S3CodeKey=$S3CodeKey \
  ContainerName="${NAME}-container" \
  Timestamp=$(date +"%s") \
  WaitForCodeBuild="Y"
rm sec-10-K-agent-cfn-packaged.yaml
```
