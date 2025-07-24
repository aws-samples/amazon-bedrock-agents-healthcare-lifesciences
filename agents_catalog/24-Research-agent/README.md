# Life Sciences Research Agent on Strands Agents (Python CDK)

## Introduction

This example deploys a life sciences research agent built with the Strands Agents SDK using the AWS Cloud Development Kit (CDK) Python version. It uses Python CDK to deploy the Python agent code to AWS Lambda.

This agent uses several tools to gather scientific information, defined in the `lambda` folder.

### search_pubmed

Use the PubMed search API to find articles from the PubMed database. By default, this tool will only return results for materials licensed for commercial use ([CC0](https://creativecommons.org/publicdomain/zero/1.0/), [CC BY](https://creativecommons.org/licenses/by/4.0/), [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/), [CC BY-ND](https://creativecommons.org/licenses/by-nd/4.0/)).

This tool will rerank the search results by the "Referenced By" count. For each article, this is the number of other articles in the search results that include it as a reference. For best results, set the "max_results" parameter to a large number (200-500) to increase the number of articles examined.

### read_pubmed

Retrieve the full text of a PubMed Central article from the [NIH NCBI PubMed Central (PMC) Article Dataset](https://aws.amazon.com/marketplace/pp/prodview-qh4qqd6ebnqio) on AWS. This product is provided as part of the [AWS Open Data Sponsorship Program](https://aws.amazon.com/marketplace/seller-profile?id=351d941c-b5a5-4250-aa21-9834ba65b1fb). The tool will download the contents of requested articles from Amazon S3 and summarize them using Amazon Bedrock to conserve space in the agent's context window.

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) installed and configured
- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) for Python package management
- [jq](https://stedolan.github.io/jq/) (optional) for formatting JSON output

## Project Structure

- `research_agent/` - Contains the CDK stack definition in Python
- `app.py` - Main CDK application entry point
- `bin/package_for_lambda.py` - Python script that packages Lambda code and dependencies into deployment archives
- `lambda/` - Contains the Python Lambda function code
- `packaging/` - Directory used to store Lambda deployment assets and dependencies

## Setup and Deployment

1. Install dependencies:

```bash
cd amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/24-Research-agent

# Install uv - see https://docs.astral.sh/uv/getting-started/installation/ for more options
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies for CDK
uv add aws-cdk-lib constructs

# Install Python dependencies for lambda with correct architecture
uv run pip install -r requirements.txt --python-version 3.12 --platform manylinux2014_aarch64 --target ./packaging/_dependencies --only-binary=:all:
```

2. Package the lambda:

```bash
uv run python ./bin/package_for_lambda.py
```

3. Bootstrap your AWS environment (if not already done):

```bash
uv run cdk bootstrap
```

4. Deploy the lambda:

```bash
uv run cdk deploy
```

## Usage

After deployment, you can invoke the Lambda function using the AWS CLI or AWS Console. The function requires proper AWS authentication to be invoked.

```bash
aws lambda invoke --function-name ResearchAgentLambda \
      --cli-binary-format raw-in-base64-out \
      --cli-read-timeout 900 \
      --payload '{"prompt": "What are some recent advances in GLP-1 drugs?"}' \
      output.json
```

If you have jq installed, you can output the response from output.json like so:

```bash
jq -r '.' ./output.json
```

Otherwise, open output.json to view the result.

## Cleanup

To remove all resources created by this example:

```bash
uv run cdk destroy
```

## Additional Resources

- [AWS CDK Python Documentation](https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-python.html)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [Python CDK API Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)