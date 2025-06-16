# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import boto3
import datetime
import json
import logging
import os
import urllib.parse
import urllib.request

session = boto3.session.Session()
secrets_manager = session.client(service_name="secretsmanager")

log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

BASE_URL = "https://api.uspto.gov/api/v1/patent/applications/search"
FUNCTION_NAMES = []
LIMIT = 25


def get_from_env_or_secretstore(SecretId: str) -> str:
    """Get the secret from the environment or secret store"""
    secret = None
    if SecretId in os.environ:
        logger.debug(f"getting {SecretId} from environment")
        secret = os.environ[SecretId].strip()
    else:
        logger.debug(f"getting {SecretId} from secrets manager")
        try:
            secret = secrets_manager.get_secret_value(SecretId=SecretId).get(
                "SecretString", ""
            )
        except Exception as e:
            logger.error(f"could not get secret {SecretId} from secrets manager: {e}")
            raise e

    return secret


try:
    API_KEY_NAME = os.environ.get("USPTO_API_KEY_NAME", "USPTO_API_KEY")
    API_KEY = get_from_env_or_secretstore(SecretId=API_KEY_NAME)
    FUNCTION_NAMES.append("uspto_search")
except Exception as e:
    logger.error(f"could not get API key: {e}")
    API_KEY = None


def uspto_search(
    search_query: str,
    filing_days_in_past: int = None,
) -> str:
    """
    Execute a search against the USPTO API

    Args:
        search_query: The query string to search for
        filing_days_in_past: Optional number of days in the past to limit search

    Returns:
        JSON string with search results
    """
    logger.info(f"executing USPTO search with {urllib.parse.quote(search_query)}")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-KEY": API_KEY,
    }
    payload = {
        "q": search_query,
        "sort": [{"field": "applicationMetaData.effectiveFilingDate", "order": "desc"}],
        "fields": [
            "applicationNumberText",
            "applicationMetaData.firstInventorName",
            "applicationMetaData.effectiveFilingDate",
            "applicationMetaData.applicationTypeLabelName",
            "applicationMetaData.firstApplicantName",
            "applicationMetaData.inventionTitle",
        ],
        "pagination": {"offset": 0, "limit": LIMIT},
    }

    if filing_days_in_past:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=int(filing_days_in_past))
        payload["rangeFilters"] = [
            {
                "field": "applicationMetaData.effectiveFilingDate",
                "valueFrom": str(start_date),
                "valueTo": str(end_date),
            }
        ]
    data = json.dumps(payload).encode("utf-8")
    logger.info(f"search payload: {data}")
    request = urllib.request.Request(BASE_URL, data=data, headers=headers)  # nosec: B310 fixed url we want to open

    try:
        response = urllib.request.urlopen(request)  # nosec: B310 fixed url we want to open
        response_data: str = response.read().decode("utf-8")
        results = json.loads(response_data)
        logger.info(f"Response from USPTO search {results}")
        return json.dumps(results, separators=(",", ":"))
    except urllib.error.HTTPError as e:
        logger.error(f"failed to retrieve search results, error: {e.code}")

    return ""


def extract_parameters(event):
    """
    Extract parameters from different event formats

    Args:
        event: Lambda event object

    Returns:
        Tuple of (search_query, days)
    """
    search_query = None
    days = None

    # Check if this is a Bedrock Agent ActionGroup format
    if "parameters" in event and isinstance(event["parameters"], list):
        for param in event["parameters"]:
            if param["name"] == "search_query":
                search_query = param["value"]
            if param["name"] == "days":
                days = param["value"]
    # Check if this is MCP format (direct key-value pairs)
    elif "search_query" in event:
        search_query = event["search_query"]
        if "days" in event:
            days = event["days"]

    return search_query, days


def format_response(query, results, event):
    """
    Format the response based on the event type

    Args:
        query: The query that was searched
        results: The results from the search
        event: The original event to determine response format

    Returns:
        Formatted response object
    """
    responseBody = {
        "TEXT": {
            "body": f"Here are the top search results for the query '{query}': {results} "
        }
    }

    # If this is a Bedrock Agent format, wrap the response accordingly
    if "messageVersion" in event:
        action_response = {
            "actionGroup": event.get("actionGroup", ""),
            "function": event.get("function", ""),
            "functionResponse": {"responseBody": responseBody},
        }

        return {
            "response": action_response,
            "messageVersion": event.get("messageVersion", "1.0"),
        }

    # For MCP format, return just the response body
    return responseBody


def lambda_handler(event, context):
    """
    Lambda handler that processes both Bedrock Agent and MCP formats

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        Response object in the appropriate format
    """
    logging.info(f"{event=}")

    # Extract parameters regardless of input format
    search_query, days = extract_parameters(event)

    # Handle missing search query
    if not search_query:
        error_body = {"TEXT": {"body": "Missing mandatory parameter: search_query"}}

        # If Bedrock Agent format, wrap the error response
        if "messageVersion" in event:
            return {
                "response": {
                    "actionGroup": event.get("actionGroup", ""),
                    "function": event.get("function", ""),
                    "functionResponse": {"responseBody": error_body},
                },
                "messageVersion": event.get("messageVersion", "1.0"),
            }
        return error_body

    # Execute the search
    search_results = uspto_search(search_query, days)
    logger.debug(f"query results {search_results=}")

    # Format and return the response
    return format_response(search_query, search_results, event)


if __name__ == "__main__":
    # Test direct function call
    search_query = "nanobody"
    filing_days_in_past = 100
    search_results = uspto_search(search_query, filing_days_in_past)
    print(f"search results: {search_results}")

    logger.info("Testing with Bedrock Agent format")
    # Test with Bedrock Agent format
    bedrock_event = {
        "messageVersion": "1.0",
        "agent": {
            "name": "test",
            "id": "ABCDEF",
            "alias": "123456",
            "version": "1",
        },
        "sessionId": "123456789",
        "actionGroup": "testGroup",
        "function": "uspto_search",
        "parameters": [
            {
                "name": "search_query",
                "value": "Nanobody",
            },
            {"name": "days", "value": "100"},
        ],
    }
    response = lambda_handler(bedrock_event, None)
    logger.info(response)

    logger.info("Testing with MCP format")
    # Test with MCP format
    mcp_event = {"search_query": "Nanobody", "days": "100"}
    response = lambda_handler(mcp_event, None)
    logger.info(response)
