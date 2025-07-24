# Create a Text2SQL Agent

Create an end-to-end Text-to-SQL Agent solution, integrated with Amazon Athena using a sample dataset

### Workflow of the Text2SQL Agent

1. **Getting the Schema**
    - Retrieves the schema for the specified SQL Database in Athena and returns to the agent

2. **Natural Language Query Processing**
    - Converts natural language questions into Amazon Athena queries
    - Executes queries against Amazon Athena
    - Returns results in user-friendly format

3. **Error handling and self-correction** : Performs a self-optimize step to improve the SQL statement before execution and also handles retries and error handling after execution

### Agentic Text2Cypher Flow

1. User asks questions to the Agent.
2. To serve the user's questions, Agent determines the appropriate action to invoke.
3. It will invoke the lambda function and execute the /getschema action to retrieve the SQL database schema.
4. The agent will use the retrieved schema to generate an SQL query.a
5. The generated query will be used as the parameter to the /queryathena action to query Athena database with the given query.
6. The lambda function will return the query results, which the agent will use to generate the natural language answer.

## Getting Started

### Deployment

Step 1: Navigate to agents_catalog/0-Notebook-environment/ and go to setup_environment.ipynb, use the Python 3 (ipykernel)

Step 2: Run through the 'sample_text2sql_agent.ipynb' to create the Text-to-SQL agent

## How to Test in AWS Console

1. Go to [Amazon Bedrock](https://console.aws.amazon.com/bedrock) and select **Agents.**

2. Select your Text-to-SQL agent and test by asking questions in **Test** window on your right. 

    Example questions can be found in the 'birdsql_data.json' which will be generated after you run through the notebook.

3. Click Show trace and examine each step to understand what tools are used and the agent's rationale for approaching your question.

## License

- [MIT-0](/LICENSE)
