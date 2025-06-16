# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from bedrock_ez_search import SemanticSearch

import boto3
import json
import logging
import os
from pathlib import Path
from rapidfuzz import process, fuzz, utils
import re
import requests
from sec_edgar_api import EdgarClient
from typing import Dict, Optional, List
import urllib
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
if log_level not in valid_log_levels:
    log_level = "INFO"
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

DEFAULT_SCORE_CUTOFF = (
    80  # Define constant for default score cutoff for cik fuzzy matching
)

# amazonq-ignore-next-line
edgar = EdgarClient(
    user_agent=os.environ.get("USER_AGENT", "AWS HCLS AGENTS").strip().upper()
)

s3 = boto3.client("s3")
s3.download_file(
    "5d1a4b76751b4c8a994ce96bafd91ec9", "us-gaap/embeddings.npy", "/tmp/embeddings.npy"
)
s3.download_file(
    "5d1a4b76751b4c8a994ce96bafd91ec9",
    "us-gaap/descriptions.csv",
    "/tmp/descriptions.csv",
)

##############################################################################
# Get CIK for company name
##############################################################################


def get_cik(
    query: str, data_file: Path, score_cutoff: int = DEFAULT_SCORE_CUTOFF
) -> Optional[Dict]:
    """
    Look up the SEC Central Index Key (CIK) for a given company name using fuzzy matching.

    Args:
        query (str): The company name to search for
        data_file (Path): Path to the JSON file containing company data
        score_cutoff (int): Minimum similarity score threshold

    Returns:
        Optional[Dict]: Company information dictionary if found, None if no match or error

    Raises:
        FileNotFoundError: If the data_file doesn't exist
        json.JSONDecodeError: If the data_file contains invalid JSON
    """
    try:
        # amazonq-ignore-next-line
        with open(data_file, "r", encoding="utf-8") as f:
            company_tickers = json.load(f)
    except IOError as e:
        logger.error(f"Error opening file {data_file}: {str(e)}")
        return None

    if not company_tickers:
        return None

    choices = [company.get("title", "") for company in company_tickers.values()]

    match = process.extractOne(
        query,
        choices,
        scorer=fuzz.WRatio,
        processor=utils.default_process,
        score_cutoff=score_cutoff,
    )
    return list(company_tickers.values())[match[2]] if match else None


##############################################################################
# Get all company facts (all tags)
##############################################################################


# def get_company_facts(cik: str) -> Dict:
#     """
#     Retrieve all company facts for a given company CIK.

#     Args:
#         cik (str): The company CIK

#     Returns:
#         Dict: A dictionary containing all of the facts for the specified company

#     Raises:
#         Exception: If there's an error retrieving company facts
#     """
#     try:
#         facts = edgar.get_company_facts(cik)
#         return facts
#     except Exception as e:
#         logger.error(f"Error retrieving company facts: {str(e)}")
#         raise


##############################################################################
# Find relevant tags for a given query
##############################################################################


def get_relevant_tags(
    query: str,
    top_k: int = 5,
    index_descriptions: Path = "/tmp/descriptions.csv",
    index_embeddings: Path = "/tmp/embeddings.npy",
) -> Dict:
    with open(index_descriptions, "r") as f:
        pattern = r"^([^,]+),([^,]+),(.+)$"
        available_facts = []
        for line in f:
            match = re.match(pattern, line.strip())
            if match:
                taxonomy, tag, description = match.groups()
                available_facts.append(
                    {
                        "taxonomy": taxonomy,
                        "tag": tag,
                        "description": description,
                    }
                )
            else:
                logger.error(f"Error parsing line: {line.strip()}")

    try:
        search = SemanticSearch(
            model_id="amazon.titan-embed-text-v2:0",  # Using v2 model
        )
        search.index(
            [i["description"] for i in available_facts if i["description"] is not None],
            embeddings_file=index_embeddings,
        )
        hits = search.search(query, top_k=top_k)

        # Get the records in available_facts that correspond to the index values for the records in search_results
        search_results = [available_facts[i["index"]] for i in hits]

        return search_results
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        return {"TEXT": {"body": f"Error during search: {str(e)}"}}


def format_relevant_tag_response(response: Dict) -> Dict:
    """
    Format the get relevant tags response into a human-readable string.

    Args:
        response (dict): The relevant tags response dictionary

    Returns:
        Dict: A dictionary containing the formatted response body
    """

    formatted_response = [
        {
            "tag": result.get("tag", ""),
            "description": result.get("description", ""),
        }
        for result in response
    ]
    return json.dumps(formatted_response, separators=(",", ":"))


def handle_find_relevant_tags(parameters) -> List[Dict]:
    """
    Handle the find_relevant_tags function.

    Args:
        parameters (list): A list of dictionaries containing the function parameters.

    Returns:
        dict: A dictionary containing the response body.
    """

    required_params = ["query"]
    missing_params = [
        param
        for param in required_params
        if not next((p["value"] for p in parameters if p["name"] == param), None)
    ]

    if missing_params:
        return {
            "TEXT": {
                "body": f"Missing mandatory parameter(s): {', '.join(missing_params)}"
            }
        }

    query = next(
        (param["value"] for param in parameters if param["name"] == "query"),
        None,
    )

    try:
        relevant_tags = get_relevant_tags(query, top_k=5)
        formatted_response = format_relevant_tag_response(relevant_tags)
        return {"TEXT": {"body": formatted_response}}
    except Exception as e:
        logger.error(f"Error in find_relevant_tags: {str(e)}")
        return {"TEXT": {"body": f"An error occurred: {str(e)}"}}


##############################################################################
# Get company facts for a specific tags
##############################################################################


def get_company_concept(cik: str, tag: str, taxonomy: str = "us-gaap") -> Dict:
    """
    Retrieve company concept information for a given CIK, taxonomy, and tag.

    Args:
        cik (str): The company CIK
        tag (str): The tag to search for
        taxonomy (str): The taxonomy to search in ("us-gaap" by default)


    Returns:
        Dict: A dictionary containing the company concept information

    Raises:
        ValueError: If there's an error with the input parameters
        requests.RequestException: If there's an error with the API request
    """
    try:
        concept = edgar.get_company_concept(cik, taxonomy, tag)
        return concept
    except ValueError as e:
        logger.error(f"Invalid input parameters: {str(e)}")
        raise
    except requests.RequestException as e:
        logger.error(f"Error retrieving company concept: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving company concept: {str(e)}")
        raise


def format_concept_response(response: Dict) -> Dict:
    """
    Format the company concept response into a human-readable string.

    Args:
        response (Dict): The company concept response dictionary

    Returns:
        Dict: A dictionary containing the formatted response body
    """

    unit, data = next(iter(response.get("units", {}).items()), [])
    short_data = [
        {
            "date": i.get("end", ""),
            "value": i.get("val", 0),
        }
        for i in data
        if i.get("form", "") == "10-K" and "frame" in i
    ]
    formatted_response = {
        "entity_name": response.get("entityName", ""),
        "label": response.get("label", ""),
        "unit": unit,
        "data": short_data,
    }
    return json.dumps(formatted_response, separators=(",", ":"))


def handle_get_company_concept(parameters: Dict):
    required_params = ["company_name", "tag"]
    missing_params = [
        param
        for param in required_params
        if not next((p["value"] for p in parameters if p["name"] == param), None)
    ]

    if missing_params:
        return {
            "TEXT": {
                "body": f"Missing mandatory parameter(s): {', '.join(missing_params)}"
            }
        }

    company_name = next(
        (param["value"] for param in parameters if param["name"] == "company_name"),
        None,
    )

    tag = next((param["value"] for param in parameters if param["name"] == "tag"), None)

    try:
        cik_info = get_cik(company_name, "cik-ref.json")
        if cik_info is None:
            return {"TEXT": {"body": f"Could not find CIK for company: {company_name}"}}
        cik = cik_info.get("cik_str", "")
        response = get_company_concept(cik, tag)
        formatted_response = format_concept_response(response)
        return {"TEXT": {"body": formatted_response}}
    except Exception as e:
        logger.error(f"Error in get_company_concept: {str(e)}")
        return {"TEXT": {"body": f"An error occurred: {str(e)}"}}


##############################################################################
# Process incoming Lambda event
##############################################################################


def process_event(event):
    """
    Process the incoming event and call the appropriate function.

    Args:
        event (dict): The event dictionary containing the function name and parameters.

    Returns:
        dict: A dictionary containing the response body and status code.
    """
    try:
        agent = event["agent"]
        actionGroup = event["actionGroup"]
        function = event["function"]
        parameters = event.get("parameters", [])
    except KeyError as e:
        logger.error(f"Missing required key in event: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required key: {str(e)}"}),
        }

    responseBody = {"TEXT": {"body": "Error, no function was called"}}

    logger.info(
        f"Agent: {urllib.parse.quote(agent['name'])}, ActionGroup: {urllib.parse.quote(actionGroup)}, Function: {urllib.parse.quote(function)}"
    )

    if function == "find_relevant_tags":
        responseBody = handle_find_relevant_tags(parameters)
    elif function == "get_company_concept":
        responseBody = handle_get_company_concept(parameters)
    else:
        responseBody = {"TEXT": {"body": f"Function {function} not implemented"}}

    action_response = {
        "actionGroup": actionGroup,
        "function": function,
        "functionResponse": {"responseBody": responseBody},
    }

    function_response = {
        "response": action_response,
        "messageVersion": event["messageVersion"],
    }

    logger.debug(f"lambda_handler: function_response={function_response}")

    return function_response


def handler(event, context):
    logger.debug(f"Event: {event}")

    return process_event(event)


if __name__ == "__main__":
    print("Testing find_relevant_tags")
    event = {
        "messageVersion": "1.0",
        "agent": {
            "name": "SEC-10-K-search-agent",
            "id": "ABCDEF",
            "alias": "123456",
            "version": "1",
        },
        "sessionId": "123456789",
        "actionGroup": "sec-10-k-search",
        "function": "find_relevant_tags",
        "parameters": [
            {"name": "query", "type": "string", "value": "Accounts payable"},
        ],
    }
    response = handler(event, None)
    print(response)
    assert (
        "AccountsPayableCurrent"
        in response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    )

    print("Testing get_company_concept")
    event = {
        "messageVersion": "1.0",
        "agent": {
            "name": "SEC-10-K-search-agent",
            "id": "ABCDEF",
            "alias": "123456",
            "version": "1",
        },
        "sessionId": "123456789",
        "actionGroup": "sec-10-k-search",
        "function": "get_company_concept",
        "parameters": [
            {"name": "company_name", "type": "string", "value": "amazon"},
            {"name": "tag", "type": "string", "value": "AccountsPayableCurrent"},
        ],
    }
    response = handler(event, None)
    print(response)
    assert (
        "AMAZON.COM, INC."
        in response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    )
