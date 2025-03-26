# Create a Bedrock Agent with your own tools

Bring your tools to Bedrock Agents

## Examples Overview 
1. [Create Agents with Function Definition](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/01-create-agent-with-function-definition)
2. [Create Agents with API Schema](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/02-create-agent-with-api-schema)

## Create Agents with a tool for your specialized model

This example utilizes a Hugging Face model from SageMaker Jumpstart and deploys it to a SageMaker endpoint and invokes via a Agent Action Group

### Workflow of the ML inference tool Agent

1. **Identify the need to invoke a specialized model**

2. **Model response Processing**
    - Trigger the action to invoke the model
    - Returns results in user-friendly format


## Getting Started

### Deployment

Step 1: Deploy the cloud formation 'jumpstart_model.yaml to deploy the model to a SageMaker endpoint and setup the invocation lambda

Step 2: Navigate to agents_catalog/0-Notebook-environment/ and go to setup_environment.ipynb, use the Python 3 (ipykernel)

Step 3: Run through the 'sample_model_inference_agent.ipynb' to create the model inference agent



## License

- [MIT-0](/LICENSE)
