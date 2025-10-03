import os
import boto3
import json
import uuid
import requests
import io
import pandas as pd
from typing import Dict, Any, List
from strands import Agent, tool
from strands.models import BedrockModel
from utils.boto3_helper import *

# Get AWS account information
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
region = boto3.Session().region_name

# Initialize AWS clients
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
sfn_client = boto3.client('stepfunctions')
s3_client = boto3.client('s3')

# Retrieve state machine and bucket information
sfn_statemachine_arn = find_state_machine_arn_by_prefix('ImagingStateMachine-')
if not sfn_statemachine_arn:
    print("Error: State machine with prefix 'ImagingStateMachine-' not found!")

s3_bucket = find_s3_bucket_name_by_suffix('-agent-build-bucket')
if not s3_bucket:
    print("Error: S3 bucket with suffix '-agent-build-bucket' not found!")
bucket_name = s3_bucket.replace("s3://", "")

print(f"Region: {region}")
print(f"Account ID: {account_id}")
print(f"State Machine: {sfn_statemachine_arn}")
print(f"S3 bucket: {s3_bucket}")

medical_imaging_agent_name = 'Medical-imaging-expert-strands'
medical_imaging_agent_description = "CT scan analysis using Strands framework"
medical_imaging_agent_instruction = """
You are a medical research assistant AI specialized in processing medical imaging scans of 
patients. Your primary task is to create medical imaging jobs, or provide relevant medical insights after the 
jobs have completed execution. Use only the appropriate tools as required by the specific question. Follow these 
instructions carefully:

1. For computed tomographic (CT) lung imaging biomarker analysis:
   a. Identify the patient subject ID(s) based on the conversation.
   b. Use the compute_imaging_biomarker tool to trigger the long-running job,
      passing the subject ID(s) as an array of strings (for example, ["R01-043", "R01-93"]).
   c. Only if specifically asked for an analysis, use the analyze_imaging_biomarker tool to process the results from the previous job.
   d. Use the retrieve_execution_status tool to confirm the execution status of a job
   e. Only analyse jobs with status completed

2. When providing your response:
   a. Start with a brief summary of your understanding of the user's query.
   b. Explain the steps you're taking to address the query. Ask for clarifications from the user if required.
   c. Present the results of the medical imaging jobs if complete.
"""

@tool
def compute_imaging_biomarker(subject_id: List[str]) -> str:
    """
    Compute the imaging biomarker features from lung CT scans within the tumor for a list of patient subject IDs.
    
    Args:
        subject_id (List[str]): An array of strings representing patient subject IDs, example ['R01-222', 'R01-333']
    
    Returns:
        str: Results of the imaging biomarker computation job
    """
    print(f"\nComputing imaging biomarkers for subjects: {subject_id}\n")
    suffix = uuid.uuid1().hex[:6]  # to be used in resource names
    processing_job_name = f'dcm-nifti-conversion-{suffix}'

    payload = {
        "PreprocessingJobName": processing_job_name,
        "Subject": subject_id
    }
    execution_response = sfn_client.start_execution(
        stateMachineArn=sfn_statemachine_arn,
        name=suffix,
        input=json.dumps(payload)
    )
    
    execution_id = execution_response['executionArn'].split(':')[-1]

    print(f"The function compute_imaging_biomarker was called successfully! Execution {execution_id} with ARN {execution_response['executionArn']} has been started.")
    return f"Imaging biomarker processing has been submitted. Results can be retrieved from your database once the job {execution_response['executionArn']} completes."

@tool
def retrieve_execution_status(execution_arn: str) -> str:
    """
    Retrieve the status of a compute execution job.
    
    Args:
        execution_arn (str): a string containing the execution arn
    
    Returns:
        str: Results the status of the execution
    """
    print(f"\nChecking status for state machine execution: {execution_arn}\n")
    response = sfn_client.describe_execution(executionArn=execution_arn)
    status = response['status']
    print(f"Execution status is {status}")
    return status

@tool
def analyze_imaging_biomarker(subject_id: List[str]) -> str:
    """
    Analyze the result imaging biomarker features from lung CT scans within the tumor for a list of patient subject IDs.
    
    Args:
        subject_id (List[str]): An array of strings representing patient subject IDs, example ['R01-222', 'R01-333']
    
    Returns:
        str: Analysis results of the imaging biomarker features
    """
    print(f"\nAnalyzing imaging biomarkers for subjects: {subject_id}\n")
    result = []
    for id in subject_id:
        output_data_uri = f'{s3_bucket}/nsclc_radiogenomics/'
        object_key = f'nsclc_radiogenomics/CSV/{id}.csv'
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            csv_data = response['Body'].read().decode('utf-8')
        
            df = pd.read_csv(io.StringIO(csv_data))
            df['subject_id'] = id
            json_data = df.to_json(orient='records')

            result = result + json.loads(json_data)
        except Exception as e:
            print(f'Error: {e}')
    
    print(f"\nAnalysis Output: {result}\n")
    return result

# Create list of tools
medical_imaging_tools = [compute_imaging_biomarker, retrieve_execution_status, analyze_imaging_biomarker]
print(f"Created {len(medical_imaging_tools)} tools for the Strands agent")

# Create Bedrock model for Strands
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name=region,
    temperature=0.1,
    streaming=False
)
