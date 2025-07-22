
import boto3
import json
import time
from collections import defaultdict
from typing import Dict, Any
from strands import Agent, tool
from strands.models import BedrockModel

# Get AWS account information
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
region = boto3.Session().region_name

# Initialize AWS clients
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
redshift_client = boto3.client('redshift-data')

print(f"Region: {region}")
print(f"Account ID: {account_id}")

biomarker_agent_name = 'Biomarker-database-analyst-strands'
biomarker_agent_description = "biomarker query engine with redshift using Strands framework"
biomarker_agent_instruction = """
You are a medical research assistant AI specialized in generating SQL queries for a 
database containing medical biomarker information. Your primary task is to interpret user queries, 
generate appropriate SQL queries, and provide relevant medical insights based on the data. 
Use only the appropriate tools as required by the specific question. Follow these instructions carefully: 

1. Before generating any SQL query, use the get_schema tool to familiarize yourself with the database structure. 
This will ensure your queries are correctly formatted and target the appropriate columns. 

2. When generating an SQL query: 
   a. Write the query as a single line, removing all newline ("\n") characters. 
   b. Column names should remain consistent, do not modify the column names in the generated SQL query. 

3. Before execution of a step: 
   a. Evaluate the SQL query with the rationale of the specific step by using the refine_sql tool. 
      Provide both the SQL query and a brief rationale for the specific step you're taking. 
      Do not share the original user question with the tool. 
   b. Only proceed to execute the query using the query_redshift tool after receiving the evaluated 
      and potentially optimized version from the refine_sql tool. 
   c. If there is an explicit need for retrieving all the data in S3, avoid optimized query 
      recommendations that aggregate the data. 

4. When providing your response: 
   a. Start with a brief summary of your understanding of the user's query. 
   b. Explain the steps you're taking to address the query. 
   c. Ask for clarifications from the user if required.
"""

def extract_table_columns(query):
    table_columns = defaultdict(list)
    for record in query["Records"]:
        table_name = record[0]["stringValue"]
        column_name = record[1]["stringValue"]
        column_type = record[2]["stringValue"]
        column_comment = record[3]["stringValue"]
        column_details = {
            "name": column_name,
            "type": column_type,
            "comment": column_comment
        }
        table_columns[table_name].append(column_details)
    return dict(table_columns)

# Define the tools using Strands @tool decorator
@tool
def get_schema() -> str:
    """
    Get the database schema including all table names and column information.
    This tool retrieves the structure of the redshift database to help formulate proper SQL queries.
    
    Returns:
        str: JSON string containing table names and their schemas
    """
    sql = """
        SELECT
            'clinical_genomic' AS table_name,
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS column_type,
            pg_catalog.col_description(a.attrelid, a.attnum) AS column_comment
        FROM
            pg_catalog.pg_attribute a
        WHERE
            a.attrelid = 'clinical_genomic'::regclass
            AND a.attnum > 0
            AND NOT a.attisdropped;"""

    try:
        result = redshift_client.execute_statement(Database='dev', DbUser='admin', Sql=sql, ClusterIdentifier='biomarker-redshift-cluster')
    
        def wait_for_query_completion(statement_id):
            while True:
                response = redshift_client.describe_statement(Id=statement_id)
                status = response['Status']
                if status == 'FINISHED':
                    break
                elif status in ['FAILED', 'CANCELLED']:
                    print("SQL statement execution failed or was cancelled.")
                    break
                time.sleep(2)
        
        wait_for_query_completion(result['Id'])
        
        response = redshift_client.get_statement_result(Id=result['Id'])
        print(f"\nSchema Output: {str(response)[:500]}...\n")
        return response
    except Exception as e:
        print("Error:", e)
        raise

@tool
def query_redshift(query: str) -> str:
    """
    Execute a SQL query against the Redshift database.
    
    Args:
        query (str): The SQL query to execute
    
    Returns:
        str: Query results as JSON string
    """
    print(f"\nRedshift Input Query: {query}\n")
    try:
        result = redshift_client.execute_statement(Database='dev', DbUser='admin', Sql=query, ClusterIdentifier='biomarker-redshift-cluster')
    
        def wait_for_query_completion(statement_id):
            while True:
                response = redshift_client.describe_statement(Id=statement_id)
                status = response['Status']
                if status == 'FINISHED':
                    break
                elif status in ['FAILED', 'CANCELLED']:
                    print("SQL statement execution failed or was cancelled.")
                    break
                time.sleep(2)
        
        wait_for_query_completion(result['Id'])
        
        response = redshift_client.get_statement_result(Id=result['Id'])
        print(f"\nRedshift Output: {response}\n")
        return response
    except Exception as e:
        print("Error:", e)
        raise

@tool
def refine_sql(sql: str, question: str) -> str:
    """
    Evaluate and potentially optimize an SQL query for efficiency.
    
    Args:
        sql (str): The SQL query to evaluate
        question (str): The rationale or step description for this query
    
    Returns:
        str: Evaluated/optimized SQL query
    """
    print(f"\nInput SQL: {sql}, Input Question: {question}\n")
    raw_schema = get_schema()
    schema = extract_table_columns(raw_schema)

    prompt = f"""
    You are an extremely critical SQL query evaluation assistant. Your job is to analyze
    the given schema, SQL query, and question to ensure the query is efficient and accurately answers the 
    question. You should focus on making the query as efficient as possible, using aggregation when applicable.

    Here is the schema you should consider:
    <schema>
    {json.dumps(schema)}
    </schema>
    
    Pay close attention to the accepted values and the column data type located in the comment field for each column.
    
    Here is the generated SQL query to evaluate:
    <sql_query>
    {sql}
    </sql_query>
    
    Here is the question that was asked:
    <question>
    {question}
    </question>
    
    Your task is to evaluate and refine the SQL query to ensure it is very efficient. Follow these steps:
    1. Analyze the query in relation to the schema and the question.
    2. Determine if the query efficiently answers the question.
    3. If the query is not efficient, provide a more efficient SQL query.
    4. If the query is already efficient, respond with "no change needed".

    When evaluating efficiency, consider the following:
    - Use of appropriate aggregation functions (COUNT, SUM, AVG, etc.)
    - Proper use of GROUP BY clauses
    - Avoiding unnecessary JOINs or subqueries
    - Selecting only necessary columns
    - Using appropriate WHERE clauses to filter data
    
    Here are examples to guide your evaluation:
    
    Inefficient query example:
    SELECT chemotherapy, survival_status FROM dev.public.lung_cancer_cases WHERE chemotherapy = 'Yes';

    This is inefficient because it does not provide a concise and informative output that directly answers
    the question. It results in a larger output size, does not aggregate the data, and presents the results
    in a format that is not easy to analyze and interpret.

    Efficient query example:
    SELECT survival_status, COUNT(*) AS count FROM dev.public.lung_cancer_cases WHERE chemotherapy = 'Yes' GROUP BY survival_status;

    This query uses COUNT(*) and GROUP BY to aggregate and count the records for each distinct value of survival_status, providing a more concise and informative result.
    
    Another efficient query example:
    SELECT smoking_status, COUNT(DISTINCT case_id) AS num_patients FROM clinical_genomic WHERE age_at_histological_diagnosis > 50 GROUP BY smoking_status;
    
    This query uses COUNT(DISTINCT) and GROUP BY to aggregate and provide a summary of the data, reducing the SQL output size.
    
    Provide your response within <efficientQuery> tags. If you suggest a new query, do not use line breaks in the generated SQL. Your response should be a single line of SQL or "no change needed" if the original query is already efficient.
    
    Remember to prioritize aggregation when possible to reduce SQL output size and provide more meaningful results.
    """
    
    try:
        user_message = {"role": "user", "content": prompt}
        claude_response = {"role": "assistant", "content": "<efficientQuery>"}
        model_Id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        messages = [user_message, claude_response]
        system_prompt = "You are an extremely critical sql query evaluation assistant, your job is to look at the schema, sql query and question being asked to then evaluate the query to ensure it is efficient."
        max_tokens = 1000
        
        body = json.dumps({
            "messages": messages,
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt
        })
    
        response = bedrock_client.invoke_model(body=body, modelId=model_Id)
        response_bytes = response.get("body").read()
        response_text = response_bytes.decode('utf-8')
        response_json = json.loads(response_text)
        content = response_json.get('content', [])
        for item in content:
            if item.get('type') == 'text':
                result_text = item.get('text')
                print(f"\nRefined SQL: {result_text}\n")
                return result_text
        return "No SQL found in response"
    except Exception as e:
        print("Error:", e)
        raise

# Create list of tools
biomarker_agent_tools = [get_schema, query_redshift, refine_sql]
print(f"Created {len(biomarker_agent_tools)} tools for the Strands agent")

# Create Bedrock model for Strands
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name=region,
    temperature=0.1,
    streaming=False
)
