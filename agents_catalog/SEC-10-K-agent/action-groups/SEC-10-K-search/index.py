# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
import logging
import os
from pathlib import Path
import pprint
from rapidfuzz import process, fuzz, utils
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
# Get all company facts (all concepts)
##############################################################################


def get_company_facts(cik: str) -> Dict:
    """
    Retrieve all company facts for a given company CIK.

    Args:
        cik (str): The company CIK

    Returns:
        Dict: A dictionary containing all of the facts for the specified company

    Raises:
        Exception: If there's an error retrieving company facts
    """
    try:
        facts = edgar.get_company_facts(cik)
        return facts
    except Exception as e:
        logger.error(f"Error retrieving company facts: {str(e)}")
        raise


# def handle_get_company_facts(parameters: Dict):
#     """
#     Handle the get_company_facts function.

#     Args:
#         parameters (list): A list of dictionaries containing the function parameters.

#     Returns:
#         dict: A dictionary containing the response body.
#     """
#     company_name = next(
#         (param["value"] for param in parameters if param["name"] == "company_name"),
#         None,
#     )

#     if not company_name:
#         return {"TEXT": {"body": "Missing mandatory parameter: company_name"}}

#     try:
#         cik_info = get_cik(company_name, "cik-ref.json")
#         if cik_info is None:
#             return {"TEXT": {"body": f"Could not find CIK for company: {company_name}"}}
#         cik = cik_info.get("cik_str", "")
#     except Exception as e:
#         logger.error(f"Error retrieving CIK: {str(e)}")
#         return {"TEXT": {"body": f"An error occurred while retrieving CIK: {str(e)}"}}

#     try:
#         response = get_company_facts(cik)
#         return {"TEXT": {"body": response}}
#     except Exception as e:
#         logger.error(f"Error in get_company_facts: {str(e)}")
#         return {
#             "TEXT": {
#                 "body": f"An error occurred while retrieving company facts: {str(e)}"
#             }
#         }


##############################################################################
# List all available facts for a given company
##############################################################################


def handle_list_available_facts(parameters) -> List[Dict]:
    """
    Handle the list_available_facts function.

    Args:
        parameters (list): A list of dictionaries containing the function parameters.

    Returns:
        dict: A dictionary containing the response body.
    """
    # amazonq-ignore-next-line
    company_name = next(
        (param["value"] for param in parameters if param["name"] == "company_name"),
        None,
    )

    if not company_name:
        return {"TEXT": {"body": "Missing mandatory parameter: company_name"}}

    try:
        cik_info = get_cik(company_name, "cik-ref.json")
        if cik_info is None:
            return {"TEXT": {"body": f"Could not find CIK for company: {company_name}"}}
        cik = cik_info.get("cik_str", "")
        facts = get_company_facts(cik)

        available_facts = [
            {
                "taxonomy": taxonomy,
                "tag": tag,
                "label": values.get("label"),
                "description": values.get("description"),
                "units": next(iter(values.get("units", {})), ""),
                "size": len(next(iter(values.get("units", {}).values()), [])),
            }
            for taxonomy, tags in facts.get("facts", {}).items()
            for tag, values in tags.items()
        ]

        return {"TEXT": {"body": available_facts}}
    except requests.RequestException as e:
        logger.error(f"Error in API request: {str(e)}")
        return {"TEXT": {"body": f"An error occurred during API request: {str(e)}"}}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON response: {str(e)}")
        return {
            "TEXT": {"body": f"An error occurred while parsing the response: {str(e)}"}
        }
    except Exception as e:
        logger.error(f"Unexpected error in list_available_facts: {str(e)}")
        return {"TEXT": {"body": f"An unexpected error occurred: {str(e)}"}}


##############################################################################
# Get company facts for a specific concepts
##############################################################################


def get_company_concept(cik: str, taxonomy: str, tag: str) -> Dict:
    """
    Retrieve company concept information for a given CIK, taxonomy, and tag.

    Args:
        cik (str): The company CIK
        taxonomy (str): The taxonomy to search in
        tag (str): The tag to search for

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
    required_params = ["company_name", "taxonomy", "tag"]
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
    taxonomy = next(
        (param["value"] for param in parameters if param["name"] == "taxonomy"), None
    )
    tag = next((param["value"] for param in parameters if param["name"] == "tag"), None)

    try:
        cik_info = get_cik(company_name, "cik-ref.json")
        if cik_info is None:
            return {"TEXT": {"body": f"Could not find CIK for company: {company_name}"}}
        cik = cik_info.get("cik_str", "")
        response = get_company_concept(cik, taxonomy, tag)
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

    if function == "get_company_concept":
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


def lambda_handler(event, context):
    logger.debug(f"Event: {event}")

    return process_event(event)


if __name__ == "__main__":
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
            {"name": "taxonomy", "type": "string", "value": "us-gaap"},
            {"name": "tag", "type": "string", "value": "AccountsPayableCurrent"},
        ],
    }
    response = lambda_handler(event, None)

    print(response)
