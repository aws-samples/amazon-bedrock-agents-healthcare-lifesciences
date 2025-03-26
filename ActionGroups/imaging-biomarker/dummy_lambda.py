import json
import logging
import uuid
import boto3
import io
import pandas as pd
import os
import ast

# Get environment variables
sfn_statemachine_name = os.environ['SFN_STATEMACHINE_NAME']
s3bucket = os.environ['S3BUCKET']
bucketname = s3bucket.replace("s3://", "")


logger = logging.getLogger()
logger.setLevel("INFO")

def lambda_handler(event, context):
    logger.info(json.dumps(event))

    # Get the current region and account ID
    region = context.invoked_function_arn.split(":")[3]
    account_id = context.invoked_function_arn.split(":")[4]

    action = event["actionGroup"]
    function = event["function"]
    parameters = event["parameters"]
    print(parameters)
    
    if function == "compute_imaging_biomarker":
        subject_id = None
        for param in parameters:
            if param["name"] == "subject_id":
                # Parse the string representation of the list
                if isinstance(param['value'], str): 
                    print("Parse the string representation of the list")
                    
                    try:
                        # Try parsing as JSON
                        subject_id =  json.loads(param["value"])
                    except json.JSONDecodeError:
                        try:
                            # Try parsing as Python literal
                            subject_id = ast.literal_eval(param["value"])
                        except (ValueError, SyntaxError):
                            # Fall back to simple string splitting
                            subject_id =  [id.strip() for id in param["value"].strip('[]').split(',')]
                else:
                    subject_id = json.loads(param["value"])
        if subject_id:
            suffix = uuid.uuid1().hex[:6]  # to be used in resource names
            
            sfn = boto3.client('stepfunctions')

            sfn_statemachine_arn = f'arn:aws:states:{region}:{account_id}:stateMachine:{sfn_statemachine_name}'
            
            processing_job_name = f'dcm-nifti-conversion-{suffix}'

            output_data_uri = f'{s3bucket}'


            payload = {
              "PreprocessingJobName": processing_job_name,
              "Subject": subject_id
            }
            execution_response = sfn.start_execution(
                stateMachineArn=sfn_statemachine_arn,
                name=suffix,
                input=json.dumps(payload)
            )  
            
            logger.info(f"The function {function} was called successfully! StateMachine {execution_response['executionArn']} has been started.")
            
            response_body = {
                "TEXT": {
                    "body": f"Imaging biomarker processing has been submitted. Results can be retrieved from your database once the job {execution_response['executionArn']} completes."
                }
            }
            
        session_attributes = {
            'sfn_executionArn': execution_response['executionArn'],
            'imaging_biomarker_output_s3': output_data_uri
        }

    elif function == "analyze_imaging_biomarker":
        subject_id = None
        result = []
        s3_client = boto3.client('s3')
        for param in parameters:
            if param["name"] == "subject_id":
                # Parse the string representation of the list
                if isinstance(param['value'], str): 
                    print("Parse the string representation of the list")
                    
                    try:
                        # Try parsing as JSON
                        subject_id =  json.loads(param["value"])
                    except json.JSONDecodeError:
                        try:
                            # Try parsing as Python literal
                            subject_id = ast.literal_eval(param["value"])
                        except (ValueError, SyntaxError):
                            # Fall back to simple string splitting
                            subject_id =  [id.strip() for id in param["value"].strip('[]').split(',')]
                else:
                    subject_id = json.loads(param["value"])
                for id in subject_id:
                    output_data_uri = f'{s3bucket}/nsclc_radiogenomics/'
                    bucket_name = bucketname
                    object_key = f'nsclc_radiogenomics/CSV/{id}.csv'
                    try:
                        print(object_key)
                        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                        csv_data = response['Body'].read().decode('utf-8')
                    
                        df = pd.read_csv(io.StringIO(csv_data))
                        df['subject_id'] = id
                        print(df.head())
                        json_data = df.to_json(orient='records')
        
                        print(json_data)
                        result = result + json.loads(json_data)
        
                    except Exception as e:
                        print(f'Error: {e}')
        
        response_body = {
            "TEXT": {
                'body': str(result)
            }
        }
    
    logger.info(f"Response body: {response_body}")

    function_response = {
        'actionGroup': action,
        'function': function,
        'functionResponse': {
            'responseBody': response_body
        }
    }
    
    session_attributes = {
        'imaging_biomarker_output_s3': output_data_uri
    }
    # prompt_session_attributes = event['promptSessionAttributes']
    
    action_response = {
        'messageVersion': '1.0', 
        'response': function_response,
        'sessionAttributes': session_attributes,
        # 'promptSessionAttributes': prompt_session_attributes
    }
    
    logger.info(f"Action response: {action_response}")
    
    return action_response
