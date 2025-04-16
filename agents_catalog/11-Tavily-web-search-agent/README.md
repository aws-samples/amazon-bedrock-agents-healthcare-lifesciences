# Tavily Web Search Agent

## 1. Summary

Answer questions using up-to-date information retrieved by the [Tavily Search API](https://tavily.com/).

## 2. Agent Details

### 2.1. Instructions

> You are a research assistant specializing in web-based information retrieval. Your task:
>
> 1. Analyze queries precisely
> 2. Search for authoritative, current sources
> 3. Deliver concise, factual responses
> 4. Include source citations
>
> Guidelines:
>
> - Communicate with clarity and precision
> - Evaluate source reliability
> - Focus on recent, relevant data
> - Decompose complex questions
> - Document search methodology
> - Request query refinement when needed
>
> Citation format:
>
> Present findings with source URLs in parentheses:
> "[Factual response] (source: [URL])"
>
> For example, if the user asks:
>
> "who built the tower of london?"
>
> And you find the answer at this url:
>
> "https://en.wikipedia.org//w/index.php?title=Tower_of_London"
>
> A good response is:
>
> "William the Conqueror built the tower of london in 1078 (source: https://en.wikipedia.org//w/index.php?title=Tower_of_London)"

### 2.2. Guardrails

| Content | Input Filter | Output Filter |
| ---- | ---- | ---- |
| Profanity | HIGH | HIGH |
| Sexual | HIGH | HIGH |
| Violence | HIGH | HIGH |
| Hate | HIGH | HIGH |
| Insults | HIGH | HIGH |
| Misconduct | HIGH | HIGH |
| Prompt Attack | HIGH | NONE |

### 2.3. Tools

```json
{
  name: "web_search",
  description: "Execute an internet search query using Tavily Search.",
  inputSchema: {
    type: "object",
    properties: {
      search_query: { type: "string", description: "The search query to execute with Tavily. Example: 'Who is Leo Messi?'"},
      target_website: { type: "string", description: "The specific website to search including its domain name. If not provided, the most relevant website will be used"},
      topic: { type: "string", description: "The topic being searched. 'news' or 'general'. Helps narrow the search when news is the focus." },
      days: { type: "string", description: "The number of days of history to search. Helps when looking for recent events or news."}
    },
    required: ["search_query"]
  }
}
```

## 3. Installation

1. (If needed) Creae a [Tavily](https://tavily.com/) account and copy your API key.
2. (If needed) Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

3. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

4. Navigate to the `Tavily-web-search-agent` folder

`cd agents_catalog/Tavily-web-search-agent`

5. Package and deploy the agent template

```bash
export BUCKET_NAME="<REPLACE>"
export STACK_NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"
export TAVILY_API_KEY="<REPLACE>"

aws cloudformation package --template-file agents_catalog/Tavily-web-search-agent/web-search-agent-cfn.yaml \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "agents_catalog/Tavily-web-search-agent/packaged-web-search-agent-cfn.yaml"
aws cloudformation deploy --template-file agents_catalog/Tavily-web-search-agent/packaged-web-search-agent-cfn.yaml \
  --capabilities CAPABILITY_IAM \
  --stack-name $STACK_NAME \
  --region $REGION \
  --parameter-overrides \
    AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM \
    TavilyApiKey=$TAVILY_API_KEY
rm agents_catalog/Tavily-web-search-agent/packaged-web-search-agent-cfn.yaml
```
