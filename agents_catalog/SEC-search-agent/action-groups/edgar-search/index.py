# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
import logging
import os
from pathlib import Path
from rapidfuzz import process, fuzz, utils
from sec_edgar_api import EdgarClient
from typing import Dict, Optional, List
import urllib
from typing import List, Dict
from pathlib import Path
import json
from txtai.embeddings import Embeddings

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

FUNCTION_NAMES = ["get_company_concept", "get_company_facts"]
DEFAULT_SCORE_CUTOFF = (
    80  # Define constant for default score cutoff for cik fuzzy matching
)

# amazonq-ignore-next-line
edgar = EdgarClient(
    user_agent=os.environ.get("USER_AGENT", "AWS HCLS AGENTS").strip().upper()
)


class TagSearchEngine:
    def __init__(self, data_file: Path):
        """
        Initialize txtai embeddings and index the tag data

        Args:
            data_file (Path): Path to the JSON file containing fact tags
        """
        # Load tag data
        with open(data_file, "r", encoding="utf-8") as f:
            self.tag_reference = json.load(f)

        # Initialize txtai embeddings
        self.embeddings = Embeddings({"path": "sentence-transformers/all-MiniLM-L6-v2"})

        # Create index data
        self.index_data = [
            (tag_name, description, None)
            for tag_name, description in self.tag_reference.items()
        ]

        # Build the similarity index
        self.embeddings.index(self.index_data)


def get_fact_tags(query: str, data_file: Path, n: int = 5) -> List[Dict]:
    """
    Find the n most relevant fact tags for a given query based on a similarity search with the description

    Args:
        query (str): The query string to search for
        data_file (Path): Path to the JSON file containing fact tags name:description pairs
        n (int): The number of relevant tags to return

    Returns:
        List: A list of dictionaries containing the most relevant fact tags and their scores
    """
    # Initialize search engine if not already created
    if not hasattr(get_fact_tags, "search_engine"):
        get_fact_tags.search_engine = TagSearchEngine(data_file)

    # Perform similarity search
    results = get_fact_tags.search_engine.embeddings.search(query, n)

    # Create results list
    facts = []
    for tag_name, score in results:
        facts.append(
            {
                "tag": tag_name,
                "description": get_fact_tags.search_engine.tag_reference[tag_name],
                "score": score,
            }
        )

    return facts


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
    with open(data_file, "r", encoding="utf-8") as f:
        company_tickers = json.load(f)

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


def get_company_concept(cik: str, taxonomy: str, tag: str) -> Dict:
    """
    Retrieve company concept information for a given CIK, taxonomy, and tag.

    Args:
        cik (str): The company CIK
        taxonomy (str): The taxonomy to search in
        tag (str): The tag to search for

    Returns:
        Dict: A dictionary containing the company concept information
    """
    try:
        concept = edgar.get_company_concept(cik, taxonomy, tag)
        return concept
    except Exception as e:
        logger.error(f"Error retrieving company concept: {str(e)}")
        return {}


def get_company_facts(cik: str) -> Dict:
    """
    Retrieve company facts for a given company CIK.

    Args:
        cik (str): The company CIK

    Returns:
        Dict: A dictionary containing the company's facts
    """
    try:
        facts = edgar.get_company_facts(cik)
        return facts
    except Exception as e:
        logger.error(f"Error retrieving company facts: {str(e)}")
        return {}


def lambda_handler(event, context):
    logging.debug(
        f"Event: {event}"
    )  # Use string formatting instead of f-string with '='

    return process_event(event)


def process_event(event):
    agent = event["agent"]
    actionGroup = event["actionGroup"]
    function = event["function"]
    parameters = event.get("parameters", [])
    responseBody = {"TEXT": {"body": "Error, no function was called"}}

    logger.info(
        f"Agent: {urllib.parse.quote(agent["name"])}, ActionGroup: {urllib.parse.quote(actionGroup)}, Function: {urllib.parse.quote(function)}"
    )

    if function in FUNCTION_NAMES:
        if function == "get_company_concept":
            responseBody = handle_get_company_concept(parameters)
        elif function == "get_company_facts":
            responseBody = handle_get_company_facts(parameters)

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


def handle_get_company_concept(parameters):
    company_name = next(
        (param["value"] for param in parameters if param["name"] == "company_name"),
        None,
    )
    taxonomy = next(
        (param["value"] for param in parameters if param["name"] == "taxonomy"), None
    )
    tag = next((param["value"] for param in parameters if param["name"] == "tag"), None)

    if not company_name:
        return {"TEXT": {"body": "Missing mandatory parameter: company_name"}}
    elif not taxonomy:
        return {"TEXT": {"body": "Missing mandatory parameter: taxonomy"}}
    elif not tag:
        return {"TEXT": {"body": "Missing mandatory parameter: tag"}}

    try:
        cik = get_cik(company_name, "cik-ref.json").get("cik_str", "")
        response = get_company_concept(cik, taxonomy, tag)
        return {"TEXT": {"body": response}}
    except Exception as e:
        logger.error(f"Error in get_company_concept: {str(e)}")
        return {"TEXT": {"body": f"An error occurred: {str(e)}"}}


def handle_get_company_facts(parameters):
    company_name = next(
        (param["value"] for param in parameters if param["name"] == "company_name"),
        None,
    )

    if not company_name:
        return {"TEXT": {"body": "Missing mandatory parameter: company_name"}}

    try:
        cik = get_cik(company_name, "cik-ref.json").get("cik_str", "")
        response = get_company_facts(cik)
        return {"TEXT": {"body": response}}
    except Exception as e:
        logger.error(f"Error in get_company_facts: {str(e)}")
        return {"TEXT": {"body": f"An error occurred: {str(e)}"}}


if __name__ == "__main__":
    for fact in get_fact_tags("Change in equity", "facts-ref.json"):
        print(fact)

    # event = {
    #     "messageVersion": "1.0",
    #     "agent": {
    #         "name": "SEC-search-agent",
    #         "id": "ABCDEF",
    #         "alias": "123456",
    #         "version": "1",
    #     },
    #     "sessionId": "123456789",
    #     "actionGroup": "edgar-search",
    #     "function": "get_company_facts",
    #     "parameters": [
    #         {"name": "company_name", "type": "string", "value": "pfizer"},
    #         {"name": "taxonomy", "type": "string", "value": "us-gaap"},
    #         {"name": "tag", "type": "string", "value": "AccountsPayableCurrent"},
    #     ],
    # }
    # with open("test.json", "w", encoding="utf-8") as f:
    #     json.dump(lambda_handler(event, None), f)
