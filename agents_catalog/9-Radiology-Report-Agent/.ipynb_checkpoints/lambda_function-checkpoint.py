import os
import boto3
from botocore.client import Config
import json
from datetime import datetime

# Environment variables
REGION = os.environ.get('REGION')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
BATCH_JOB_QUEUE = os.environ.get('BATCH_JOB_QUEUE')
BATCH_JOB_DEFINITION_FEATURE_EXTRACTION = os.environ.get('BATCH_JOB_DEFINITION_FEATURE_EXTRACTION')
BATCH_JOB_DEFINITION_CLASSIFIER = os.environ.get('BATCH_JOB_DEFINITION_CLASSIFIER')
LAMBDA_VIEWER_FUNCTION_NAME = os.environ.get('LAMBDA_VIEWER_FUNCTION_NAME')

# Bedrock configuration
BEDROCK_CONFIG = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})

# Initialize clients
s3_client = boto3.client('s3')
sagemaker_runtime = boto3.client('runtime.sagemaker')
bedrock_agent_client = boto3.client("bedrock-agent-runtime", region_name=REGION, config=BEDROCK_CONFIG)
batch_client = boto3.client('batch')

def run_validator(text):
    response = "This is the response " +  text
    return response

def create_response(status_code, body):
    return {
        "statusCode": status_code,
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    responseBody = {
        "TEXT": { "body": "Error, Function call didn't happen"}
    }
    print("Parameters: ", parameters)
    print('Function: ', function)
    if function == 'run_validator':
        responseBody = run_validator(parameters[0]["pat_report"])


    action_response = {
        "actionGroup": actionGroup,
        "function": function,
        "functionResponse": {"responseBody": responseBody} }

    function_response = {'response': action_response, "messageVersion": event["messageVersion"]}
    return function_response


if __name__ == "__main__":
    import os 
    os.environ["AWS_PROFILE"]="default"
    event = {
        "actionGroup": "actionGroup",
        "function": "run_validator",
        "parameters": [{"pat_report": "rest report"} ],
        "messageVersion": "1.0"
    }

    print(lambda_handler(event, None))
        