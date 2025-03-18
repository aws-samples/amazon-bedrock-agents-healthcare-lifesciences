# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
import logging
import os
import urllib.parse
import urllib.request

import boto3

session = boto3.session.Session()
secrets_manager = session.client(service_name="secretsmanager")

log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

FUNCTION_NAMES = []


def get_from_secretstore_or_env(SecretId: str) -> str:
    try:
        secret_value = secrets_manager.get_secret_value(SecretId=SecretId)
    except Exception as e:
        logger.error(f"could not get secret {SecretId} from secrets manager: {e}")
        raise e

    SecretString: str = secret_value["SecretString"]

    return SecretString


try:
    TAVILY_API_KEY_NAME = os.environ.get("TAVILY_API_KEY_NAME", "")
    TAVILY_API_KEY = get_from_secretstore_or_env(SecretId=TAVILY_API_KEY_NAME)
    FUNCTION_NAMES.append("web_search")
except Exception as e:
    TAVILY_API_KEY = None


def web_search(
    search_query: str, target_website: str = "", topic: str = None, days: int = None
) -> str:
    logger.info(f"executing Tavily AI search with {search_query=}")

    base_url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": search_query,
        "search_depth": "advanced",
        "include_images": False,
        "include_answer": False,
        "include_raw_content": False,
        "max_results": 3,
        "topic": "general" if topic is None else topic,
        "days": 30 if days is None else days,
        "include_domains": [target_website] if target_website else [],
        "exclude_domains": [],
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base_url, data=data, headers=headers)  # nosec: B310 fixed url we want to open

    try:
        response = urllib.request.urlopen(request)  # nosec: B310 fixed url we want to open
        response_data: str = response.read().decode("utf-8")
        logger.debug(f"response from Tavily AI search {response_data=}")
        return response_data
    except urllib.error.HTTPError as e:
        logger.error(
            f"failed to retrieve search results from Tavily AI Search, error: {e.code}"
        )

    return ""


def lambda_handler(event, context):
    logging.debug(f"{event=}")

    agent = event["agent"]
    actionGroup = event["actionGroup"]
    function = event["function"]
    parameters = event.get("parameters", [])
    responseBody = {"TEXT": {"body": "Error, no function was called"}}

    logger.info(f"{agent=}\n{actionGroup=}\n{function=}")

    if function in FUNCTION_NAMES:
        if function == "web_search":
            search_query = None
            target_website = None
            topic = None
            days = None

            for param in parameters:
                if param["name"] == "search_query":
                    search_query = param["value"]
                if param["name"] == "target_website":
                    target_website = param["value"]
                if param["name"] == "topic":
                    topic = param["value"]
                if param["name"] == "days":
                    days = param["value"]

            if not search_query:
                responseBody = {
                    "TEXT": {"body": "Missing mandatory parameter: search_query"}
                }
            else:
                search_results = web_search(search_query, target_website, topic, days)
                responseBody = {
                    "TEXT": {
                        "body": f"Here are the top search results for the query '{search_query}': {search_results} "
                    }
                }

                logger.debug(f"query results {search_results=}")
    else:
        TAVILY_API_KEY_NAME = os.environ.get("TAVILY_API_KEY_NAME", "")
        responseBody = {
            "TEXT": {"body": f"Unable to get {TAVILY_API_KEY_NAME} Secret Key"}
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
