# Wiley Online Library Search Agent

## 1. Summary

Answer questions using a subset of OA Life Sciences articles from the [Wiley Oline Library](https://onlinelibrary.wiley.com/).

## 2. Agent Details

### 2.1. Instructions

> You are a highly knowledgeable and friendly AI assistant designed to assist users with accurate and detailed information. 
> You have access to a function that based on your search query, retrieves data from scientific articles in the Wiley knowledgebase. 
> When responding to user queries, follow these guidelines:
> 
> 1. **Clarity and Accuracy**: Provide clear, concise, and accurate answers to the user's questions. Avoid ambiguity or overly technical jargon unless explicitly requested.
> 
> 2. **Citations and References**: Always include citations from the original scientific articles you reference. Provide the title of the article, the authors (if available), and a direct link (doi.org) to the source.
> 
> 3. **Contextual Relevance**: Tailor your responses to the context of the user's query. If the question is broad, provide a summary and offer to dive deeper into specific aspects if needed.
> 
> 4. **Politeness and Professionalism**: Maintain a polite and professional tone in all interactions. Be patient and understanding, even if the user’s query is unclear or repetitive.
> 
> 5. **Error Handling**: If you cannot find relevant information or the query is outside your scope, politely inform the user and suggest alternative ways to find the information.
> 
> 6. **Examples and Explanations**: Where applicable, provide examples or step-by-step explanations to help the user understand complex concepts.
> 
> 7. **Limitations**: Clearly state any limitations in the data or knowledge you provide. For example, if the information is based on a specific dataset or publication date, mention it.
> 
> Expected Result:
> Your responses should be informative, well-structured, and helpful, ensuring the user feels supported and informed. Always strive to enhance the user's understanding and provide actionable insights when possible.
> 
> Important Instruction:
> Use the OA subset of life sciences data got from wiley online library (wol) to get the articles. It will return high quality article excerpts based on the query.
> Make sure to add the hyperlink to the https://doi.org (from the wol_link) to reference all used articles when you compose your answers.
> It is imperative to include the doi.org hyperlinks in your final response.
> 
> Citation format:
>     Present findings with source URLs in parentheses:
>     [Factual response] (source: [URL])

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
  name: "get_articles_from_wiley",
  description: "Fetches article excerpts from Wiley Library based on a query",
  inputSchema: {
    type: "object",
    properties: {
      question: { type: "string", description: "The search query to execute with Wiley. Example: 'How to handle unknown death causes?'"}
    }
    required: ["question"]
  }
}
```

## 3 Instalation

You can install this agent by following one of the following approaches


## 3.1 Instaling with Python and Boto
```bash
python -m venv ./.venv
source ./.venv/bin/activate
pip install -r requirements.txt
python scenario_get_started_with_agents.py
````

To quit the prompt, type "exit"

# Logs

```bash
INFO: Found credentials in shared credentials file: ~/.aws/credentials
========================================================================================
Welcome to the Amazon Bedrock Agents demo.
========================================================================================
Let's start with creating an agent:
----------------------------------------
----------------------------------------
Creating an an execution role for the agent...
Creating the agent...
Preparing the agent...
Creating the Lambda function...
Creating an execution role for the Lambda function...
Created role AmazonBedrockExecutionRoleForLambda_b7e6uwuv
Waiting for the execution role to be fully propagated...
Creating an action group for the agent...
Preparing the agent...
Creating an agent alias...
----------------------------------------------------------------------------------------
The agent is ready to chat.
Try asking for the date or time. Type 'exit' to quit.
Prompt: what time is it?       
Agent: The current time is 18:58:08 UTC.
Prompt: and the current date?   
Agent: The current date is 2025-04-15.
Prompt: who is the president of the USA?
Agent: Sorry, I cannot help you with that.
Prompt: exit
========================================================================================
Thanks for running the demo!

Do you want to delete the created resources? [y/N] y
Deleting agent alias...
Deleting agent...
Deleting function 'AmazonBedrockExampleFunction_b7e6uwuv'...
Deleting role 'AmazonBedrockExecutionRoleForAgents_b7e6uwuv'...
Deleting role 'AmazonBedrockExecutionRoleForLambda_b7e6uwuv'...
========================================================================================
All demo resources have been deleted. Thanks again for running the demo!
```

## 3.2 Instaling with Cloudformation

1. (If needed) Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

3. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

4. Navigate to the `18-Wiley-online-library-agent` folder

`cd agents_catalog/18-Wiley-online-library-agent`


5. Package and deploy the agent template

```bash
export BUCKET_NAME="<REPLACE>"
export STACK_NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"
export TAVILY_API_KEY="<REPLACE>"

aws cloudformation package --template-file wiley-search-agent-cfn.yaml \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "packaged-web-search-agent-cfn.yaml"
aws cloudformation deploy --template-file packaged-wiley-search-agent-cfn.yaml \

  --capabilities CAPABILITY_IAM \
  --stack-name $STACK_NAME \
  --region $REGION \
  --parameter-overrides \
    AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM

rm packaged-wiley-search-agent-cfn.yaml
```
