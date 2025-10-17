import boto3
import time
import os
import uuid
import json
import sys
from collections import defaultdict

redshift_client = boto3.client('redshift-data')

def refineSQL(sql, question):
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
    client = boto3.client('bedrock-runtime')
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
    
    response = client.invoke_model(body=body, modelId=model_Id)
    response_bytes = response.get("body").read()
    response_text = response_bytes.decode('utf-8')
    response_json = json.loads(response_text)
    content = response_json.get('content', [])
    for item in content:
        if item.get('type') == 'text':
            result_text = item.get('text')
            print(result_text)
            return result_text
    
    return "No SQL found in response"

def get_schema():
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
        print("SQL statement execution started. StatementId:", result['Id'])
    
        def wait_for_query_completion(statement_id):
            while True:
                response = redshift_client.describe_statement(Id=statement_id)
                status = response['Status']
                if status == 'FINISHED':
                    print("SQL statement execution completed.")
                    break
                elif status in ['FAILED', 'CANCELLED']:
                    print("SQL statement execution failed or was cancelled.")
                    break
                print("Waiting for SQL statement execution to complete...")
                time.sleep(5)
        
        wait_for_query_completion(result['Id'])
        
        response = redshift_client.get_statement_result(Id=result['Id'])
        return response
    except Exception as e:
        print("Error:", e)
        raise

def query_redshift(query):
    try:
        result = redshift_client.execute_statement(Database='dev', DbUser='admin', Sql=query, ClusterIdentifier='biomarker-redshift-cluster')
        print("SQL statement execution started. StatementId:", result['Id'])
    
        def wait_for_query_completion(statement_id):
            while True:
                response = redshift_client.describe_statement(Id=statement_id)
                status = response['Status']
                if status == 'FINISHED':
                    print("SQL statement execution completed.")
                    break
                elif status in ['FAILED', 'CANCELLED']:
                    print("SQL statement execution failed or was cancelled.")
                    break
                print("Waiting for SQL statement execution to complete...")
                time.sleep(5)
        
        wait_for_query_completion(result['Id'])
        
        response = redshift_client.get_statement_result(Id=result['Id'])
        return response
    except Exception as e:
        print("Error:", e)
        raise

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

def upload_result_s3(result, bucket, key):
    s3 = boto3.resource('s3')
    s3object = s3.Object(bucket, key)
    s3object.put(Body=(bytes(json.dumps(result).encode('UTF-8'))))
    return s3object

def lambda_handler(event, context):
    result = None
    error_message = None

    try:
        if event['apiPath'] == "/getschema":
            raw_schema = get_schema()
            result = extract_table_columns(raw_schema)

        elif event['apiPath'] == "/refinesql":
            params =event['parameters']
            for param in params:
                if param.get("name") == "sql":
                    sql = param.get("value")
                    print(sql)
                if param.get("name") == "question":
                    question = param.get("value")
                    print(question)
                
            result = refineSQL(sql, question)
        
        elif event['apiPath'] == "/queryredshift":
            params =event['parameters']
            for param in params:
                if param.get("name") == "query":
                    query = param.get("value")
                    print(query)
                
            result = query_redshift(query)

        else:
            raise ValueError(f"Unknown apiPath: {event['apiPath']}")

        if result:
            print("Query Result:", result)
    
    except Exception as e:
        error_message = str(e)
        print(f"Error occurred: {error_message}")

    BUCKET_NAME = os.environ['BUCKET_NAME']
    KEY = str(uuid.uuid4()) + '.json'
    size = sys.getsizeof(str(result)) if result else 0
    print(f"Response size: {size} bytes")
    
    if size > 20000:
        print('Size greater than 20KB, writing to a file in S3')
        result = upload_result_s3(result, BUCKET_NAME, KEY)
        response_body = {
            'application/json': {
                'body': f"Result uploaded to S3. Bucket: {BUCKET_NAME}, Key: {KEY}"
            }
        }
    else:
        response_body = {
            'application/json': {
                'body': str(result) if result else error_message
            }
        }

    action_response = {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': 200 if result else 500,
        'responseBody': response_body
    }

    # session_attributes = event['sessionAttributes']
    # prompt_session_attributes = event['promptSessionAttributes']
    
    api_response = {
        'messageVersion': '1.0', 
        'response': action_response,
        # 'sessionAttributes': session_attributes,
        # 'promptSessionAttributes': prompt_session_attributes
    }
        
    return api_response
