import os
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load CDM from external JSON file
CDM_PATH = './cdm.json'

def load_cdm():
    try:
        with open(CDM_PATH, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Failed to load CDM: {e}")
        return {}

def lambda_handler(event, context):
    
    agent = event.get('agent', '')
    actionGroup = event.get('actionGroup', '')
    function = event.get('function', '')
    parameter_list = event.get('parameters', [])

    logger.info("Lambda invoked")
    logger.info(f"Agent: {agent}, Function: {function}, ActionGroup: {actionGroup}")

    clinical_protocol_cdm = load_cdm()

    logger.info(f"cdm loaded: {clinical_protocol_cdm}")

    try:
        if function != "getClinicalProtocolTemplate":
            raise ValueError(f"Unsupported function: {function}")

        # Ignore specific 'sections' parameter, always return full CDM
        response_body = {
            "TEXT": {
                "body": f"Here is the full Clinical Document Model (CDM) : {clinical_protocol_cdm}"
            }
        }

        function_response = {
            "actionGroup": actionGroup,
            "function": function,
            "functionResponse": {
                "responseBody": response_body
            }
        }

    except Exception as e:
        logger.error(f"[ERROR] {str(e)}")
        response_body = {
            "TEXT": {
                "body": f"An error occurred: {str(e)}"
            }
        }
        function_response = {
            "actionGroup": actionGroup,
            "function": function,
            "functionResponse": {
                "responseState": "FAILURE",
                "responseBody": response_body
            }
        }

    return {
        "messageVersion": "1.0",
        "response": function_response,
        "sessionAttributes": event.get("sessionAttributes", {}),
        "promptSessionAttributes": event.get("promptSessionAttributes", {})
    }
