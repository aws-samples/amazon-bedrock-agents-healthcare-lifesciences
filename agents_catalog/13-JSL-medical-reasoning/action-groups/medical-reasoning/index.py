# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import boto3
import json
import logging
import os
from typing import Dict

log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

session = boto3.session.Session()
sagemaker = session.client("sagemaker-runtime")

# Get the Sagemaker endpoint name from the environment variables
endpoint_names = []
env = "ENDPOINT_NAME_1"
endpoint_name = os.environ.get(env, None)
if not endpoint_name:
    raise Exception(f"{env} environment variable is not set")
endpoint_names.append(endpoint_name)


def call_sagemaker_endpoint(text: str, endpoint_name: str) -> Dict:
    """
    Invoke a sagemaker endpoint with a text string
    """
    logger.debug(f"call_sagemaker_endpoint: {text=}, {endpoint_name=}")

    prompt = {
        "model": "/opt/ml/model",
        "messages": [
            {
                "role": "system",
                "content": "You are a medical expert that reviews the problem, does reasoning, and then gives a final answer.\nStrictly follow this exact format for giving your output:\n\n<think>\nreasoning steps\n</think>\n\n**Final Answer**: [Conclusive Answer]",
            },
            {"role": "user", "content": text},
        ],
        "max_tokens": 2048,
        "temperature": 0.8,
        "top_p": 0.95,
    }

    # Call the Sagemaker endpoint
    response = sagemaker.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps(prompt),
        ContentType="application/json",
    )

    # Parse the response
    response_body = json.loads(response["Body"].read().decode("utf-8"))
    return json.dumps(response_body, separators=(",", ":"))


def lambda_handler(event, context):
    logging.debug(f"{event=}")

    agent = event["agent"]
    actionGroup = event["actionGroup"]
    function = event["function"]
    parameters = event.get("parameters", [])
    responseBody = {"TEXT": {"body": "Error, no function was called"}}

    logger.info(f"{agent=}\n{actionGroup=}\n{function=}")

    medical_text = None

    for param in parameters:
        if param["name"] == "medical_text":
            medical_text = param["value"]

    if not medical_text:
        responseBody = {"TEXT": {"body": "Missing mandatory parameter: medical_text"}}
    else:
        if function == "consult_with_medical_reasoning_model":
            sm_results = call_sagemaker_endpoint(
                medical_text, endpoint_name=endpoint_names[0]
            )
        else:
            responseBody = {"TEXT": {"body": f"Error, unknown function: {function}"}}

        responseBody = {
            "TEXT": {
                "body": f"Here are the results from the {function} function:\n{sm_results} "
            }
        }

    action_response = {
        "actionGroup": actionGroup,
        "function": function,
        "functionResponse": {"responseBody": responseBody},
    }

    function_response = {
        "response": action_response,
        "messageVersion": event["messageVersion"],
    }

    logger.debug(f"lambda_handler: {function_response=}")

    return function_response


if __name__ == "__main__":
    logger.info("Testing consult_with_medical_reasoning_model")

    prompt = "How do emerging mRNA technologies compare to traditional vaccine approaches for disease prevention?"
    event = {
        "messageVersion": "1.0",
        "agent": {
            "name": "test",
            "id": "ABCDEF",
            "alias": "123456",
            "version": "1",
        },
        "sessionId": "123456789",
        "actionGroup": "testGroup",
        "function": "consult_with_medical_reasoning_model",
        "parameters": [
            {
                "name": "medical_text",
                "value": prompt,
            }
        ],
    }
    response = lambda_handler(event, None)
    logger.info(response)
