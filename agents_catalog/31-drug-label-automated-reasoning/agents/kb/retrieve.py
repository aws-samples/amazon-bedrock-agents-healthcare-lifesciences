# retrieve.py

import json
import logging
import os
from typing import Any, Dict, List

import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

KENDRA_INDEX_ID = os.environ.get("KENDRA_INDEX_ID")

logger.debug(f"Kendra Index Id is {KENDRA_INDEX_ID}")

# 1. Tool Specification
TOOL_SPEC = {
    "name": "retrieve",
    "description": "Retrieve relevant passages from Amazon Kendra index.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "query_text": {
                    "type": "string",
                    "description": "The search query text",
                },
            },
            "required": ["query_text"],
        }
    },
}


def _error_response(error_code: str, message: str, context: Any) -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        "success": False,
        "errorCode": error_code,
        "message": message,
        "requestId": context.aws_request_id if context else None,
    }


def retrieve(tool, **kwargs: Any):
    """
    Retrieve relevant passages from Amazon Kendra index.

    Args:
        query_text: The search query text
        product: Optional product name to filter results

    Returns:
        Dict containing Kendra retrieve results
    """

    # Extract tool parameters
    tool_use_id = tool["toolUseId"]
    tool_input = tool["input"]

    # Get parameter values
    query_text = tool_input.get("query_text")
    product = tool_input.get("product")

    try:
        # Get environment variables
        if not KENDRA_INDEX_ID:
            raise ValueError("KENDRA_INDEX_ID environment variable is required")

        logger.info(
            f"Retrieving from Kendra index: {KENDRA_INDEX_ID}, query: {query_text}, product: {product}"
        )

        # Initialize Kendra client
        kendra_client = boto3.client("kendra")

        # Build the retrieve request
        retrieve_params = {
            "IndexId": KENDRA_INDEX_ID,
            "QueryText": query_text,
            "PageSize": 10,  # Limit results for testing
        }

        # Add product filter if specified
        if product:
            retrieve_params["AttributeFilter"] = {
                "EqualsTo": {"Key": "product", "Value": {"StringValue": product}}
            }
            logger.info(f"Applied product filter: {product}")

        # Call Kendra retrieve
        response = kendra_client.retrieve(**retrieve_params)

        # Process results
        result_items = response.get("ResultItems", [])
        logger.info(f"Retrieved {len(result_items)} passages")

        # Format response
        formatted_results = []
        for item in result_items:
            formatted_item = {
                "title": item.get("DocumentTitle"),
                "data": item.get("Content"),
                "confidence": item.get("ScoreAttributes", {}).get("ScoreConfidence"),
            }
            formatted_results.append(formatted_item)

        logger.info(f"Retrieve operation completed successfully")
        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [
                {
                    "json": {
                        "success": True,
                        "query": query_text,
                        "results": formatted_results,
                    }
                }
            ],
        }

    except Exception as e:
        logger.info(f"Error in retrieve: {str(e)}")
        raise
