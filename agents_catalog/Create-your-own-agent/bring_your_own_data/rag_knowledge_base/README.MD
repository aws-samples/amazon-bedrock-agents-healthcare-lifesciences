# Create a RAG Agent

Create a sample end-to-end RAG Agent solution.

## Sample Database Overview

This notebook will walk users through setting up a sample RAG Agent with a sample text dataset, using the Amazon Bedrock knowledgebase feature.

### RAG Flow

1. User asks questions to the agent.
2. To serve the user's questions, Agent determines the appropriate action to invoke.
3. It will invoke the knowledge base to perform RAG and retrieve relevant references
4. The agent will use the retrieved references to generate a natural language answer.

## Getting Started

### Deployment

Step 1: Navigate to agents_catalog/0-Notebook-environment/ and go to setup_environment.ipynb, use the Python 3 (ipykernel)

Step 2: Run through the 'sample_rag_agent.ipynb' to create the RAG agent

## How to Test in AWS Console

1. Go to [Amazon Bedrock](https://console.aws.amazon.com/bedrock) and select **Agents.**

2. Select your RAG agent and test by asking questions in **Test** window on your right. 

    Example questions can be found in the 'question_and_answers.json' which will be generated after you run through the notebook.

3. Click Show trace and examine each step to understand what tools are used and the agent's rationale for approaching your question.

## License

- [MIT-0](/LICENSE)
