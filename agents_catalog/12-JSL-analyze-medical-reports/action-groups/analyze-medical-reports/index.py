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
for i in range(1, 3):
    env = "ENDPOINT_NAME_" + str(i)
    endpoint_name = os.environ.get(env, None)
    if not endpoint_name:
        raise Exception(f"{env} environment variable is not set")
    endpoint_names.append(endpoint_name)


def call_sagemaker_endpoint(text: str, endpoint_name: str) -> Dict:
    """
    Invoke a sagemaker endpoint with a text string
    """
    logger.debug(f"call_sagemaker_endpoint: {text=}, {endpoint_name=}")
    # Call the Sagemaker endpoint
    response = sagemaker.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps({"text": text}),
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
        if function == "extract_social_determinants_of_health":
            ade_results = call_sagemaker_endpoint(
                medical_text, endpoint_name=endpoint_names[0]
            )
        elif function == "extract_icd_10_cm_sentence_entities":
            ade_results = call_sagemaker_endpoint(
                medical_text, endpoint_name=endpoint_names[1]
            )
        else:
            responseBody = {"TEXT": {"body": f"Error, unknown function: {function}"}}

        responseBody = {
            "TEXT": {
                "body": f"Here are the results from the {function} function:\n{ade_results} "
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


# if __name__ == "__main__":
#     logger.info("Testing extract_social_determinants_of_health")
#     event = {
#         "messageVersion": "1.0",
#         "agent": {
#             "name": "test",
#             "id": "ABCDEF",
#             "alias": "123456",
#             "version": "1",
#         },
#         "sessionId": "123456789",
#         "actionGroup": "testGroup",
#         "function": "extract_social_determinants_of_health",
#         "parameters": [
#             {
#                 "name": "medical_text",
#                 "value": "I was asked by Dr. X to see the patient in consultation for a new diagnosis of colon cancer. The patient presented to medical attention after she noticed mild abdominal cramping in February 2007. At that time, she was pregnant and was unsure if her symptoms might have been due to the pregnancy. Unfortunately, she had miscarriage at about seven weeks. She again had abdominal cramping, severe, in late March 2007. She underwent colonoscopy on 04/30/2007 by Dr. Y. Of note, she is with a family history of early colon cancers and had her first colonoscopy at age 35 and no polyps were seen at that time. On colonoscopy, she was found to have a near-obstructing lesion at the splenic flexure. She was not able to have the scope passed past this lesion. Pathology showed a colon cancer, although I do not have a copy of that report at this time. She had surgical resection done yesterday. The surgery was laparoscopic assisted with anastomosis. At the time of surgery, lymph nodes were palpable. Pathology showed colon adenocarcinoma, low grade, measuring 3.8 x 1.7 cm, circumferential and invading in to the subserosal mucosa greater than 5 mm, 13 lymph nodes were negative for metastasis. There was no angiolymphatic invasion noted. Radial margin was 0.1 mm. Other margins were 5 and 6 mm. Testing for microsatellite instability is still pending.",
#             }
#         ],
#     }
#     response = lambda_handler(event, None)
#     logger.info(response)

#     logger.info("Testing extract_icd_10_cm_sentence_entities")
#     event = {
#         "messageVersion": "1.0",
#         "agent": {
#             "name": "test",
#             "id": "ABCDEF",
#             "alias": "123456",
#             "version": "1",
#         },
#         "sessionId": "123456789",
#         "actionGroup": "testGroup",
#         "function": "extract_icd_10_cm_sentence_entities",
#         "parameters": [
#             {
#                 "name": "medical_text",
#                 "value": "I was asked by Dr. X to see the patient in consultation for a new diagnosis of colon cancer. The patient presented to medical attention after she noticed mild abdominal cramping in February 2007. At that time, she was pregnant and was unsure if her symptoms might have been due to the pregnancy. Unfortunately, she had miscarriage at about seven weeks. She again had abdominal cramping, severe, in late March 2007. She underwent colonoscopy on 04/30/2007 by Dr. Y. Of note, she is with a family history of early colon cancers and had her first colonoscopy at age 35 and no polyps were seen at that time. On colonoscopy, she was found to have a near-obstructing lesion at the splenic flexure. She was not able to have the scope passed past this lesion. Pathology showed a colon cancer, although I do not have a copy of that report at this time. She had surgical resection done yesterday. The surgery was laparoscopic assisted with anastomosis. At the time of surgery, lymph nodes were palpable. Pathology showed colon adenocarcinoma, low grade, measuring 3.8 x 1.7 cm, circumferential and invading in to the subserosal mucosa greater than 5 mm, 13 lymph nodes were negative for metastasis. There was no angiolymphatic invasion noted. Radial margin was 0.1 mm. Other margins were 5 and 6 mm. Testing for microsatellite instability is still pending.",
#             }
#         ],
#     }
#     response = lambda_handler(event, None)
#     logger.info(response)
