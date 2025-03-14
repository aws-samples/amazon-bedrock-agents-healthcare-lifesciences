import boto3
import time
import os
import uuid
import json
import sys
from collections import defaultdict
from langchain_community.graphs import NeptuneGraph
import langchain

import requests
import json
from urllib.parse import quote

NEPTUNE_HOST = os.environ['NEPTUNE_HOST']
NEPTUNE_PORT = os.environ['NEPTUNE_PORT']
graph =  NeptuneGraph(host = NEPTUNE_HOST, port=NEPTUNE_PORT)

#Return the neptune database schema
def get_schema(question):
    print("Getting Schema")
    schema = graph.schema
    system_prompt = """You are a graph database expert. Your task is to analyze a user's query and the full database schema, then return only the relevant portions of the schema that are needed to answer the query. 
    
    Consider:
    1. The node labels and their properties mentioned in the query
    2. The relationships that would be needed to connect these nodes
    3. Any properties that might be used for filtering or returning results
    
    Return only the relevant parts of the schema in the same format as the input schema."""

    prompt = f"""I have a graph database query and I need to identify the relevant parts of the schema to answer it.

    Query: {question}

    Full Schema:
    {schema}

    Please analyze the query and return only the portions of the schema that are directly relevant to answering this query. 
    Maintain the same schema format but include only the necessary nodes, relationships, and properties."""

    print("Prompting Claude")
    client = boto3.client('bedrock-runtime')
    model_Id = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
    

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100000,
        "temperature": 0,
        "messages": [
            {
                "role": "assistant",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    })

    print("Invoking Claude")

    try:    
        response = client.invoke_model(body=body, modelId=model_Id, trace="ENABLED")
    except Exception as e:
        print("Error invoking Claude:", e)
        raise

    print("Claude invoked")
    response_bytes = response.get("body").read()
    response_text = response_bytes.decode('utf-8')
    response_json = json.loads(response_text)
    content = response_json.get('content', [])
    for item in content:
        if item.get('type') == 'text':
            result_text = item.get('text')
            print(result_text)
            return result_text
    
    return "No schema was returned"

#Query the Neptune database
def query_neptune(query):
    print("Querying Neptune")
    try:
        # Construct the full URL for the OpenCypher endpoint
        url = f'https://{NEPTUNE_HOST}:{NEPTUNE_PORT}/openCypher'

        # Set up the headers
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        # Prepare the data (URL-encode the query)
        data = f'query={quote(query)}'

        # Send the POST request
        response = requests.post(url, headers=headers, data=data, verify=True)

        # Check if the request was successful
        response.raise_for_status()

        # Parse the JSON response
        result = response.json()

        return result

    except requests.exceptions.RequestException as e:
        print("Error executing Neptune query:", e)
        raise

    except json.JSONDecodeError as e:
        print("Error parsing JSON response:", e)
        raise

    except Exception as e:
        print("Unexpected error:", e)
        raise
      
def upload_result_s3(result, bucket, key):
    s3 = boto3.resource('s3')
    s3object = s3.Object(bucket, key)
    s3object.put(Body=(bytes(json.dumps(result).encode('UTF-8'))))
    return s3object

def lambda_handler(event, context):
    result = None
    error_message = None
    schema = None

    try:
        print(event)
        if event['apiPath'] == "/getschema":
            question = event['inputText']
            result = get_schema(question)
            schema = result
        
        elif event['apiPath'] == "/queryneptune":
            params =event['parameters']
            for param in params:
                if param.get("name") == "query":
                    query = param.get("value")
                    print(query)
                
            result = query_neptune(query)

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
    response_body = None

    if size > 20000:
        print('Size greater than 20KB, writing to a file in S3')
        result = upload_result_s3(result, BUCKET_NAME, KEY)

        try:
            s3_client = boto3.client('s3')
            presigned_url = s3_client.generate_presigned_url('get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': KEY},
                ExpiresIn=3600
            )

            response_body = {
                'application/json': {
                    'body': json.dumps({
                        'type': 'presigned_url',
                        'url': presigned_url
                        })
                }
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }

        # response_body = {
        #     'application/json': {
        #         'body': f"Result uploaded to S3. Bucket: {BUCKET_NAME}, Key: {KEY}"
        #     }
        # }
    else:
        print("In response body")
        response_body = {
            'application/json': {
                'body': str(result) if result else error_message
            }
        }

    print(response_body)
    action_response = {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': 200,
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