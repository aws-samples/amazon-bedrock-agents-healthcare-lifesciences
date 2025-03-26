import boto3
import time
import os
import uuid
import json
import sys
from collections import defaultdict

athena_client = boto3.client('athena')
    
def get_schema(database_name="california_schools"):
    """
    Get schema information for all tables in Athena databases
    """

    sql = f"""
        SELECT
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = '{database_name}'
        ORDER BY table_name, ordinal_position;
        """
        
    try:
        # Start query execution
        response = athena_client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={
                'Database': database_name
            }
        )
            
        query_execution_id = response['QueryExecutionId']
            
        def wait_for_query_completion(query_execution_id):
            while True:
                response = athena_client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                state = response['QueryExecution']['Status']['State']
                
                if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    print(f"Query {state}")
                    return state
                    
                print("Waiting for query to complete...")
                time.sleep(2)
            
        # Wait for query completion
        state = wait_for_query_completion(query_execution_id)

        if state == 'SUCCEEDED':
            # Get query results
            results = athena_client.get_query_results(
                QueryExecutionId=query_execution_id
            )
            print("Got query results for schema")
            # Assuming you have a database connection and cursor setup
            # cursor.execute(sql)
            # results = cursor.fetchall()
            
            database_structure = []
            table_dict = {}

            # Skip the header row
            rows = results['ResultSet']['Rows'][1:]

            for row in rows:
                # Extract values from the Data structure
                table_name = row['Data'][0]['VarCharValue']
                column_name = row['Data'][1]['VarCharValue']
                data_type = row['Data'][2]['VarCharValue']
                
                # Initialize table if not exists
                if table_name not in table_dict:
                    table_dict[table_name] = []
                
                # Append column information
                table_dict[table_name].append((column_name, data_type))

            # Convert to the desired format
            for table_name, columns in table_dict.items():
                database_structure.append({
                    "table_name": table_name,
                    "columns": columns
                })

            return database_structure

        else:
            raise Exception(f"Query failed with state: {state}")
    except Exception as e:
            print(f"Error getting schema: {e}")
            raise

def query_athena(query, database_name='california_schools'):
    """
    Execute a query on Athena
    """
    try:
        # Start query execution
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={
                'Database': database_name
            }
        )
        
        query_execution_id = response['QueryExecutionId']
        
        def wait_for_query_completion(query_execution_id):
            while True:
                response = athena_client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                state = response['QueryExecution']['Status']['State']
                
                if state == 'FAILED':
                    error_message = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                    raise Exception(f"Query failed: {error_message}")
                    
                if state == 'CANCELLED':
                    raise Exception("Query was cancelled")
                    
                if state == 'SUCCEEDED':
                    return state
                    
                print("Waiting for query to complete...")
                time.sleep(2)
        
        # Wait for query completion
        state = wait_for_query_completion(query_execution_id)
        print("query complete")
        # Get query results
        print(state)

        if state == 'SUCCEEDED':
            results = athena_client.get_query_results(
                QueryExecutionId=query_execution_id
            )
            print("got query results")
            print(results)
            # Process results
            processed_results = []
            headers = []
            
            # Get headers from first row
            if results['ResultSet']['Rows']:
                headers = [field.get('VarCharValue', '') for field in results['ResultSet']['Rows'][0]['Data']]
            
            # Process data rows
            for row in results['ResultSet']['Rows'][1:]:
                values = [field.get('VarCharValue', '') for field in row['Data']]
                row_dict = dict(zip(headers, values))
                processed_results.append(row_dict)
            
            print(processed_results)
            return processed_results

        else:
            raise Exception(f"Query failed with state: {state}")
        
    except Exception as e:
        print(f"Error executing query: {e}")
        raise

def upload_result_s3(result, bucket, key):
    s3_client = boto3.client('s3')
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(result)
    )
    return {
        "storage": "s3",
        "bucket": bucket,
        "key": key
    }

def lambda_handler(event, context):
    result = None
    error_message = None

    try:
        if event['apiPath'] == "/getschema":
            result = get_schema()
        
        elif event['apiPath'] == "/queryathena":
            params =event['parameters']
            for param in params:
                if param.get("name") == "query":
                    query = param.get("value")
                    print(query)
                
            result = query_athena(query)
            print("end of query ")

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
    
    api_response = {
        'messageVersion': '1.0', 
        'response': action_response,
    }
        
    return api_response