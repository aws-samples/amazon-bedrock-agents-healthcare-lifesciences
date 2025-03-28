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

# Bedrock configuration
BEDROCK_CONFIG = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})

# Initialize clients
s3_client = boto3.client('s3')
sagemaker_runtime = boto3.client('runtime.sagemaker')
bedrock_agent_client = boto3.client("bedrock-agent-runtime", region_name=REGION, config=BEDROCK_CONFIG)
batch_client = boto3.client('batch')

def create_response(status_code, body):
    """Create a standardized API response"""
    return {
        'statusCode': status_code,
        'body': json.dumps(body)
    }

def retrieve_and_generate(input_prompt, document_s3_uri, sourceType="S3"):
    """Execute Bedrock retrieve and generate operation"""
    if sourceType == "S3":
        return bedrock_agent_client.retrieve_and_generate(
            input={
                'text': input_prompt
            },
            retrieveAndGenerateConfiguration={
                'type': 'EXTERNAL_SOURCES',
                'externalSourcesConfiguration': {
                    'modelArn': f'arn:aws:bedrock:{REGION}::foundation-model/{MODEL_ID}',
                    "sources": [
                        {
                            "sourceType": sourceType,
                            "s3Location": {
                                "uri": document_s3_uri
                            }
                        }
                    ]
                }
            }
        )
    else:
        raise NotImplementedError("Expects an S3 URI Location")

def get_s3_object(prefix):
    """Search for an object in S3 with given prefix"""
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if 'Contents' not in response or not response['Contents']:
        return None
    return response['Contents'][0]['Key']

def retrieve_existing_pathology_report(patient_id):
    if not patient_id:
        return create_response(400, {'error': 'patient_id is required'})

    # Search for the pathology report in S3
    document_key = get_s3_object(f"REPORTS/{patient_id}")
    if not document_key:
        return create_response(404, {'error': f'No pathology report found for patient_id: {patient_id}'})
    
    prompt = "Extract the pathology report as a json object, tumor type, grade type, microinstability status. If the information is not present, return None"
    report = retrieve_and_generate(prompt, f"s3://{BUCKET_NAME}/{document_key}")

    return create_response(200, {
        's3_uri': f"s3://{BUCKET_NAME}/{document_key}",
        'result': report.get('output', {}).get('text', 'No output text')
    })

def wsi_feature_extraction(patient_id):
    if not patient_id:
        return create_response(400, {'error': 'patient_id is required'})

    # Search for the pathology report in S3
    wsi_key = get_s3_object(f"WSI/{patient_id}")
    if not wsi_key:
        return create_response(404, {'error': f'No WSI file found for patient_id: {patient_id}'})
    
    s3_wsi_uri = f"s3://{BUCKET_NAME}/{wsi_key}"
    aws_batch_job_name = f"extract_features_{patient_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    aws_batch_container_overrides = {
        "environment": [
            {'name': 'HF_HOME', 'value':'/dev/shm'},
            {'name': 'TMP_DIR', 'value': '/dev/shm'},
            {'name': 'FILE_NAME', 'value': s3_wsi_uri},
            {'name': 'BUCKET_NAME', 'value': BUCKET_NAME},
        ],
        'resourceRequirements': [
            {'value': '1', 'type': 'VCPU'},
            {'value': '15000','type': 'MEMORY'},
            {'value': '1','type': 'GPU'}
        ]
    }

    response = batch_client.submit_job(
        jobName=aws_batch_job_name,
        jobQueue=BATCH_JOB_QUEUE,
        jobDefinition=BATCH_JOB_DEFINITION_FEATURE_EXTRACTION,
        containerOverrides=aws_batch_container_overrides
    )
    job_id = response['jobId']
    return create_response(200, {'jobId': f"started a Feature Extraction Job with job id: {job_id}"})

def wsi_msi_classification(patient_id):
    if not patient_id:
        return create_response(400, {'error': 'patient_id is required'})

    # Search for the pathology report in S3
    wsi_features_key = get_s3_object(f"FEATURES/{patient_id}")
    if not wsi_features_key:
        return create_response(404, {'error': f'No Features found for patient_id: {patient_id}, please extract features first !'})
    

    s3_features_uri = f"s3://{BUCKET_NAME}/{wsi_features_key}"
    aws_batch_job_name = f"msi_classification_{patient_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    aws_batch_container_overrides = {
        "environment": [
            {'name': 'FILE_NAME', 'value': s3_features_uri},
            {'name': 'BUCKET_NAME', 'value': BUCKET_NAME},
        ],
        'resourceRequirements': [
            {'value': '1', 'type': 'VCPU'},
            {'value': '15000','type': 'MEMORY'},
            {'value': '1','type': 'GPU'}
        ]
    }

    response = batch_client.submit_job(
        jobName=aws_batch_job_name,
        jobQueue=BATCH_JOB_QUEUE,
        jobDefinition=BATCH_JOB_DEFINITION_FEATURE_EXTRACTION,
        containerOverrides=aws_batch_container_overrides
    )
    job_id = response['jobId']
    return create_response(200, {'jobId': f"started a MSI Classification Job with job id: {job_id}. Check back later"})

def check_on_aws_batch_job_status(jobId):
    """Helper function to check on AWS Batch Job status"""
    response = batch_client.describe_jobs(jobs=[jobId])
    job_status = response['jobs'][0]['status']
    return create_response(200, {'jobId': jobId, 'status': job_status})

def check_on_executed_ml_models(patient_id):
    if not patient_id:
        return create_response(400, {'error': 'patient_id is required'})
    
    prexisting_file_key = get_s3_object(f"PREDICTIONS/{patient_id}")
    if prexisting_file_key:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=prexisting_file_key)
        file_content = response['Body'].read().decode('utf-8')
        return create_response(200, {'result': f"Classification was executed in the past and result was: {file_content}"})
    
    preexisting_features_key = get_s3_object(f"FEATURES/{patient_id}")
    if not preexisting_features_key:
        return create_response(200, {'error': f'No Features found for patient_id: {patient_id}, please extract features first !'})

def lambda_handler(event, context):
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    responseBody =  {
        "TEXT": {
            "body": "Error, no function was called"
        }
    }

    if function == 'retrieve_existing_pathology_report':
        patient_id = None
        for param in parameters:
            if param["name"] == "patient_id":
                patient_id = param["value"]

        if not patient_id:
            raise Exception("Missing mandatory parameter: patient_id")
        pathology_report = retrieve_existing_pathology_report(patient_id)
        responseBody =  {
            'TEXT': {
                "body": f"Pathology report for patient {patient_id}: {pathology_report}"
            }
        }
    elif function == 'wsi_feature_extraction':
        patient_id = None
        for param in parameters:
            if param["name"] == "patient_id":
                patient_id = param["value"]

        feature_extraction_job = wsi_feature_extraction(patient_id)

        responseBody =  {
            'TEXT': {
                "body": f"Feature Extraction for patient {patient_id} started with job: {feature_extraction_job}"
            }
        }
    elif function == 'retrieve_msi_status':
        patient_id = None
        for param in parameters: 
            if param["name"] == "patient_id":
                patient_id = param["value"] 
        
        msi_status_job = wsi_msi_classification(patient_id)
        responseBody =  {
            'TEXT': {
                "body": f"MSI Classification started  with job: {msi_status_job}"
            }
        }

    elif function == 'check_on_aws_batch_job_status':
        jobId = None
        for param in parameters:
            if param["name"] == "jobId":
                jobId = param["value"]

        job_status = check_on_aws_batch_job_status(jobId)
        responseBody =  {
            'TEXT': {
                "body": f"Job status for job {jobId}: {job_status}"
            }
        }
    
    elif function == 'check_on_executed_ml_models':
        patient_id = None
        for param in parameters:
            if param["name"] == "patient_id":
                patient_id = param["value"]

        prexisting_jobs_results = check_on_executed_ml_models(patient_id)
        responseBody =  {
            'TEXT': {
                "body": str(json.dumps(prexisting_jobs_results))
            }
        }

    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(function_response))

    return function_response

if __name__ == "__main__":
    # Example usage
    import os
    os.environ['AWS_PROFILE'] = 'pidemal-hcls'
    event = {
        "actionGroup": "actionGroup",
        "function": "retrieve_existing_pathology_report",
        "parameters": [
            {"name": "patient_id", "value": "TCGA-3L"}
        ],
        "messageVersion": "1.0"
    }
    print(check_on_aws_batch_job_status("jobID"))
    
