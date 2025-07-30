
import boto3
import json
import uuid
import requests
from typing import Dict, Any, List
from strands import Agent, tool
from strands.models import BedrockModel

# Get AWS account information
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
region = boto3.Session().region_name

# Lambda function configuration (reusing existing infrastructure)
medical_imaging_lambda_function_name = "imaging-biomarker-lambda"  # Change if different in your account
medical_imaging_lambda_function_arn = f"arn:aws:lambda:{region}:{account_id}:function:{medical_imaging_lambda_function_name}"

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=region)
bedrock_client = boto3.client('bedrock-runtime', region_name=region)

print(f"Lambda function ARN: {medical_imaging_lambda_function_arn}")
print(f"Region: {region}")
print(f"Account ID: {account_id}")

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

2. When providing your response:
   a. Start with a brief summary of your understanding of the user's query.
   b. Explain the steps you're taking to address the query. Ask for clarifications from the user if required.
   c. Present the results of the medical imaging jobs if complete.
"""

def invoke_lambda_function(operation: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Helper function to invoke the existing Lambda function with Bedrock Agent compatible event structure
    """
    if payload is None:
        payload = {}
    
    # Convert subject_id list to JSON string to match Lambda function expectations
    subject_id_list = payload.get('subject_id', [])
    subject_id_value = json.dumps(subject_id_list)
    
    print(f"DEBUG: Original subject_id: {subject_id_list}")
    print(f"DEBUG: JSON string subject_id: {subject_id_value}")
    print(f"DEBUG: Type of JSON string: {type(subject_id_value)}")
    
    # Prepare the event payload to match what the Lambda function expects from Bedrock Agents
    if operation == 'compute_imaging_biomarker':
        event = {
            'actionGroup': 'imagingBiomarkerProcessing',
            'function': 'compute_imaging_biomarker',
            'parameters': [
                {
                    'name': 'subject_id',
                    'type': 'string',  # Changed from 'array' to 'string' since we're sending JSON
                    'value': subject_id_value
                }
            ],
            'sessionAttributes': {},
            'promptSessionAttributes': {}
        }
    elif operation == 'analyze_imaging_biomarker':
        event = {
            'actionGroup': 'imagingBiomarkerProcessing',
            'function': 'analyze_imaging_biomarker',
            'parameters': [
                {
                    'name': 'subject_id',
                    'type': 'string',  # Changed from 'array' to 'string' since we're sending JSON
                    'value': subject_id_value
                }
            ],
            'sessionAttributes': {},
            'promptSessionAttributes': {}
        }
    else:
        raise ValueError(f"Unknown operation: {operation}")
    
    print(f"DEBUG: Event structure being sent: {json.dumps(event, indent=2)}")
    
    try:
        response = lambda_client.invoke(
            FunctionName=medical_imaging_lambda_function_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        print(f"DEBUG: Lambda invocation successful")
        
        result = json.loads(response['Payload'].read())
        print(f"DEBUG: Lambda response: {json.dumps(result, indent=2)}")
        
        # Extract the actual result from the Bedrock Agent response format
        if 'response' in result and 'responseBody' in result['response']:
            response_body = result['response']['responseBody']
            if 'application/json' in response_body:
                body_content = response_body['application/json']['body']
                
                # Try to parse as JSON if it looks like JSON
                if isinstance(body_content, str):
                    try:
                        if body_content.startswith('{') or body_content.startswith('['):
                            return json.loads(body_content)
                        else:
                            return body_content
                    except json.JSONDecodeError:
                        return body_content
                else:
                    return body_content
        
        return result
        
    except Exception as e:
        print(f"DEBUG: Exception during Lambda invocation: {str(e)}")
        return {"error": str(e)}

# Define the tools using Strands @tool decorator
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
    result = invoke_lambda_function('compute_imaging_biomarker', {'subject_id': subject_id})
    print(f"\nComputation Output: {json.dumps(result, indent=2)}\n")
    return json.dumps(result, indent=2)

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
    result = invoke_lambda_function('analyze_imaging_biomarker', {'subject_id': subject_id})
    print(f"\nAnalysis Output: {json.dumps(result, indent=2)}\n")
    return json.dumps(result, indent=2)

# Create list of tools
medical_imaging_tools = [compute_imaging_biomarker, analyze_imaging_biomarker]
print(f"Created {len(medical_imaging_tools)} tools for the Strands agent")

# Create Bedrock model for Strands
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name=region,
    temperature=0.1,
    streaming=False
)
