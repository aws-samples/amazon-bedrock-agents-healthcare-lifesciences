import json
import logging
import urllib.request
import urllib.error

WILEY_ONLINE_LIBRARY = "https://51xu00806d.execute-api.us-east-1.amazonaws.com/api?question="

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Lambda started")
    logger.info(f"Event data: {event}")

    response_code = 200

    # Extract the 'question' parameter from the 'parameters' list
    question = None
    for param in event.get('parameters', []):
        if param.get('name') == 'question':
            question = param.get('value')
            break

    if question:
        logger.info(f"Received query parameter 'question': {question}")
    else:
        response_code = 400
        response_body = {"text/plain": {"body": "Query parameter 'question' is missing"}}
        logger.warning("Query parameter 'question' is missing")


    if response_code == 200: 
        try:
            # Encode the question parameter to escape special characters
            encoded_question = urllib.parse.quote(question)
            with urllib.request.urlopen(WILEY_ONLINE_LIBRARY + encoded_question) as response:
                charset = response.headers.get_content_charset() or 'utf-8'
                external_data = response.read().decode(charset)
                json_data = json.loads(external_data)
                logger.info(f"Received external data: {json_data}")
                response_body = {"application/json": {"body": json_data}}

        except urllib.error.URLError as e:
            response_body = {"text/plain": {"body": f"Request failed: {e.reason}"}}
            response_code = 500

        except json.JSONDecodeError:
            response_body = {"text/plain": {"body": "Failed to parse JSON response"}}
            response_code = 500

    action_response = {
        "actionGroup": event["actionGroup"],
        "apiPath": event["apiPath"],
        "httpMethod": event["httpMethod"],
        "httpStatusCode": response_code,
        "responseBody": response_body,
    }

    session_attributes = event.get("sessionAttributes", {})
    prompt_session_attributes = event.get("promptSessionAttributes", {})

    return {
        "messageVersion": "1.0",
        "response": action_response,
        "sessionAttributes": session_attributes,
        "promptSessionAttributes": prompt_session_attributes,
    }
