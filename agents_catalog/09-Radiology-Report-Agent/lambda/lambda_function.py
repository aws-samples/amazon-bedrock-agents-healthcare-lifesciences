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
bedrock_agent_client = boto3.client("bedrock-runtime", region_name=REGION, config=BEDROCK_CONFIG)
batch_client = boto3.client('batch')



def download_guidance_document(anatomical_structure):
    """The function downloads the appropriate documents from the S3 bucket
    for validating the report. The documents are downloaded to the local
    directory where the lambda function is running. 
    """
    print("Downloading guidance document")
    import boto3
    import os
    # Get list of all files in the S3 bucket
    s3 = boto3.client('s3')
    bucket_name = "radiologyreport-validator"
    response = s3.list_objects_v2(Bucket=bucket_name)
    files = [obj['Key'] for obj in response['Contents']]

    s3_resource = boto3.resource('s3')
    download_dir = '/tmp'  # Lambda function has access to /tmp directory

    print("Anatomical structure: ", anatomical_structure)

    print("Files: ", files)
    res_files = []
    for _file in files:
        if anatomical_structure.title() in _file and _file.endswith(".pdf"):
            print(_file)
            response = s3.get_object(Bucket=bucket_name, Key=_file)
            # download the file object from S3 to local using boto3
            # Get the basename of the file
            basename = os.path.basename(_file)
            s3_resource.Bucket(bucket_name).download_file(_file, 
                            os.path.join(download_dir, basename))
            res_files.append(basename)
            print("Downloaded guidance document")
            # Here are the downloaded files 
            print(os.listdir(download_dir))
            
    if len(res_files) > 0:
        return 'SUCCESS'
    else:
        return 'FAILURE'
            
    
        
def run_validator(text):
    validation_document_dir = '/tmp'
    validation_documents = os.listdir(validation_document_dir)
    if len(validation_documents) == 0:
        return "No validation documents found. Please upload the validation documents to the S3 bucket."
    elif len(validation_documents) > 0:
        
        prompt_postpend = "Does the above radiology report adheres to the ACR guidelines mentioned in the document? \
        Is it detailed enough to provide a diagnosis? \
        Is the report missing any key anatomical structures? \
        Does the report meet the \
        quality standards of the ACR guidelines? Please provide a terse actionable feedback and do not try to summarize the report itself. ?"
        prompt = prompt_postpend + " " + text

        val_doc = os.path.join(validation_document_dir,validation_documents[0])
        print("Validation document: ", val_doc)
        with open(val_doc, 'rb') as file:
            pdf_bytes = file.read()
        messages =[
        {
        "role": "user",
        "content": [
        {
            "document": {
                "format": "pdf",
                "name": "DocumentPDFmessages",
                "source": {
                    "bytes":  pdf_bytes
                }
            }
        },
        {"text": prompt        }
        ]
        }
        ]
        inf_params = {"maxTokens": 200, "topP": 0.1, "temperature": 0.3}
        model_response = bedrock_agent_client.converse(modelId=MODEL_ID, messages=messages, inferenceConfig=inf_params)
        response_text = model_response['output']['message']['content'][0]['text']
        print("***************Tested***************")
        return response_text




def create_response(status_code, body):
    return {
        "statusCode": status_code,
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    # responseBody = {
    #     "TEXT": { "body": "Error, Function call didn't happen"}
    # }
    print("Parameters: ", parameters)
    print('Function: ', function)
    if function == 'run_validator':
        result  = run_validator(parameters[0]["value"])
        responseBody= { 
            "TEXT": {"body": result}
        }
    elif function == 'download_guidance_document':
        print("For downloading the guidance document")
        print("Parameters: ", parameters)
        result = download_guidance_document(parameters[0]["value"])
        print("Result: ", result)
        if result == 'SUCCESS':
            responseBody = {
                "TEXT": {"body": "Guidance document downloaded successfully"}
            }
        else:
            responseBody = {
                "TEXT": {"body": "Error downloading guidance document"}
            }
    else:
        responseBody = {
            "TEXT": {"body": "Error, Function not found"}
        }


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
    print("Hello")
    main()
    
    
        