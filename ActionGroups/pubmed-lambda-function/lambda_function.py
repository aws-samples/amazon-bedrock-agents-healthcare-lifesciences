import json
import logging
logger = logging.getLogger()
logger.setLevel("INFO")

from PubMed import PubMed
pubmed = PubMed()


def lambda_handler(event, context):
    logger.info(json.dumps(event))

    action = event["actionGroup"]
    api_path = event["apiPath"]
    parameters = event["parameters"]
    http_method = event["httpMethod"]
    
    if api_path == "/query-pubmed":
        body = pubmed.run(parameters[0]["value"])
        response_body = {"application/json": {"body": str(body)}}
        response_code = 200
    else:
        # If the api path is not recognized, return an error message
        body = {"{}::{} is not a valid api, try another one.".format(action, api_path)}
        response_code = 400
        response_body = {"application/json": {"body": str(body)}}
    
    logger.info(f"Response body: {response_body}")

    action_response = {
        'actionGroup': action,
        'apiPath': api_path,
        'httpMethod': http_method,
        'httpStatusCode': response_code,
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
