# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import boto3
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

FUNCTION_NAMES = []


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
    TAVILY_API_KEY_NAME = os.environ.get("TAVILY_API_KEY_NAME", "TAVILY_API_KEY")
    TAVILY_API_KEY = get_from_env_or_secretstore(SecretId=TAVILY_API_KEY_NAME)
    FUNCTION_NAMES.append("web_search")
except Exception as e:
    logger.error(f"could not get API key: {e}")
    TAVILY_API_KEY = None


def web_search(
    search_query: str, target_website: str = "", topic: str = None, days: int = None
) -> str:
    """
    Execute a search against the Tavily AI API
    
    Args:
        search_query: The query string to search for
        target_website: Optional website to limit search to
        topic: Optional topic category for the search
        days: Optional number of days in the past to limit search
        
    Returns:
        JSON string with search results
    """
    logger.info(f"executing Tavily AI search with {urllib.parse.quote(search_query)}")

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
            f"failed to retrieve search results, error: {e.code}"
        )

    return ""


def extract_parameters(event):
    """
    Extract parameters from different event formats
    
    Args:
        event: Lambda event object
        
    Returns:
        Dictionary of parameters
    """
    params = {
        "search_query": None,
        "target_website": None,
        "topic": None,
        "days": None
    }
    
    # Check if this is a Bedrock Agent ActionGroup format
    if "parameters" in event and isinstance(event["parameters"], list):
        for param in event["parameters"]:
            if param["name"] in params:
                params[param["name"]] = param["value"]
    # Check if this is MCP format (direct key-value pairs)
    else:
        for key in params:
            if key in event:
                params[key] = event[key]
            
    return params


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
    params = extract_parameters(event)
    
    # Handle missing search query
    if not params["search_query"]:
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
    search_results = web_search(
        params["search_query"], 
        params["target_website"], 
        params["topic"], 
        params["days"]
    )
    logger.debug(f"query results {search_results=}")
    
    # Format and return the response
    return format_response(params["search_query"], search_results, event)


if __name__ == "__main__":
    # Test direct function call
    search_query = "artificial intelligence"
    search_results = web_search(search_query, days=30)
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
        "function": "web_search",
        "parameters": [
            {
                "name": "search_query",
                "value": "artificial intelligence",
            },
            {"name": "days", "value": "30"},
        ],
    }
    response = lambda_handler(bedrock_event, None)
    logger.info(response)
    
    logger.info("Testing with MCP format")
    # Test with MCP format
    mcp_event = {
        "search_query": "artificial intelligence",
        "days": "30"
    }
    response = lambda_handler(mcp_event, None)
    logger.info(response)