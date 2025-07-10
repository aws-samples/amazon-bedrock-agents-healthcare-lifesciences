# PubMed Research Agent on Strands Agents

## Introduction

The example deploys a PubMed research agent application that requires AWS authentication to invoke the Lambda function. It uses a TypeScript-based CDK (Cloud Development Kit) example to deploy the Python agent code AWS Lambda. 

This agent uses tools to find and read scientific articles from the PubMed database. These tools have some special features to help the agent focus on the most relevant articles:

- It limits the search to only articles licensed for commercial use
- For each article in the search results, the tool calculates how many OTHER articles include it as a reference. These are likely to be the most impactful and valuable to the agent.

You can view the tool code in thr `lambda` folder

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) installed and configured
- [Node.js](https://nodejs.org/) (v18.x or later)
- Python 3.12 or later
- [jq](https://stedolan.github.io/jq/) (optional) for formatting JSON output

## Project Structure

- `lib/` - Contains the CDK stack definition in TypeScript
- `bin/` - Contains the CDK app entry point and deployment scripts:
  - `cdk-app.ts` - Main CDK application entry point
  - `package_for_lambda.py` - Python script that packages Lambda code and dependencies into deployment archives
- `lambda/` - Contains the Python Lambda function code
- `packaging/` - Directory used to store Lambda deployment assets and dependencies

## Setup and Deployment

1. Install dependencies:

```bash
# Install Node.js dependencies including CDK and TypeScript locally
npm install

# Create a Python virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies for lambda with correct architecture
pip install -r requirements.txt --python-version 3.12 --platform manylinux2014_aarch64 --target ./packaging/_dependencies --only-binary=:all:
```

2. Package the lambda:

```bash
python ./bin/package_for_lambda.py
```

3. Bootstrap your AWS environment (if not already done):

```bash
npx cdk bootstrap
```

4. Deploy the lambda:

```
npx cdk deploy
```

## Usage

After deployment, you can invoke the Lambda function using the AWS CLI or AWS Console. The function requires proper AWS authentication to be invoked.

```bash
aws lambda invoke --function-name PubMedResearchAgentLambda \
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
npx cdk destroy
```

## Additional Resources

- [AWS CDK TypeScript Documentation](https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-typescript.html)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
