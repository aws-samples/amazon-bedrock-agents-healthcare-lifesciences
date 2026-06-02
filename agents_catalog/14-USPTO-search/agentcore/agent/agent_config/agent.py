"""USPTO Patent Search Agent with @tool functions."""

import datetime
import json
import logging
import os
import urllib.parse
import urllib.request

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

BASE_URL = "https://api.uspto.gov/api/v1/patent/applications/search"
LIMIT = 25
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """# Patent Search Assistant Instructions

You are a specialized assistant leveraging Claude Sonnet 4.5 to help users search the USPTO patent database. Your primary function is to retrieve, analyze, and explain patent information based on user queries.

## How to Help Users

1. When users ask about patents, help them formulate effective search queries by:
  - Clarifying technical terminology
  - Identifying key search terms
  - Suggesting appropriate search parameters (date ranges, classifications, etc.)

2. After retrieving patent information:
  - Always return the application number
  - Always return the applicant name
  - Always return the effective filing date
  - Summarize key details in plain language
  - Explain technical concepts found in patents
  - Highlight important claims and applications
  - Identify assignees and filing dates

Always maintain a helpful, informative tone while translating complex patent language into clear explanations for users of all technical backgrounds.
"""


def _get_api_key() -> str:
    """Retrieve USPTO API key from environment or AWS Secrets Manager."""
    key_name = os.environ.get("USPTO_API_KEY_NAME", "USPTO_API_KEY")

    if key_name in os.environ:
        return os.environ[key_name].strip()

    client = boto3.client("secretsmanager")
    return client.get_secret_value(SecretId=key_name)["SecretString"]


@tool(
    name="uspto_search",
    description="Search the USPTO Open Data system for patent applications. Returns application numbers, applicant names, filing dates, and invention titles.",
)
def uspto_search(search_query: str, days: str = None) -> str:
    """Search USPTO patent database.

    Args:
        search_query: The search query to execute with USPTO. Example: 'Nanobodies'
        days: Optional number of days of history to search. Helps when looking for recent patents.

    Returns:
        JSON string with patent search results.
    """
    api_key = _get_api_key()

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-KEY": api_key,
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

    if days:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=int(days))
        payload["rangeFilters"] = [
            {
                "field": "applicationMetaData.effectiveFilingDate",
                "valueFrom": str(start_date),
                "valueTo": str(end_date),
            }
        ]

    data = json.dumps(payload).encode("utf-8")
    logger.info(f"USPTO search payload: {data}")
    request = urllib.request.Request(BASE_URL, data=data, headers=headers)  # nosec: B310

    try:
        response = urllib.request.urlopen(request)  # nosec: B310
        response_data = response.read().decode("utf-8")
        results = json.loads(response_data)
        logger.info(f"USPTO search returned {len(results.get('results', []))} results")
        return json.dumps(results, separators=(",", ":"))
    except urllib.error.HTTPError as e:
        logger.error(f"USPTO search failed: {e.code}")
        return json.dumps({"error": f"USPTO API returned HTTP {e.code}"})


def create_agent() -> Agent:
    """Create and return the USPTO Patent Search Agent."""
    model = BedrockModel(model_id=MODEL_ID)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[uspto_search],
    )
